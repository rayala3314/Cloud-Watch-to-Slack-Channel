# TODO:
    # create role to allow listing of tags on sns


# Create an IAM role for the lambda function -- Pass in all sns topic arn's
resource "aws_iam_role" "send_cloudwatch_alarms_to_slack" {
  name = "send-cloudwatch-alarms-to-slack"

  assume_role_policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
POLICY
}

resource "aws_iam_policy" "send_cloudwatch_alarms_to_slack_test" {
    name = "send-cloudwatch-alarms-to-slack-test"

   policy = <<EOF
{
"Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sns:ListTagsForResource",
            "Resource": "${aws_sns_topic.slack_alerts.arn}"
        }
]
}
EOF
}

# Allow lambda to write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "send_cloudwatch_alarms_to_slack_basic" {
  role       = aws_iam_role.send_cloudwatch_alarms_to_slack.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "send_cloudwatch_alarms_to_slack_basic_test" {
  role       = aws_iam_role.send_cloudwatch_alarms_to_slack.name
  policy_arn = "${aws_iam_policy.send_cloudwatch_alarms_to_slack_test.arn}"
}

# Create ZIP archive with a lambda function
data "archive_file" "send_cloudwatch_alarms_to_slack" {
  type = "zip"

  source_dir  = "../${path.module}/functions/send-cloudwatch-alarms-to-slack"
  output_path = "../${path.module}/functions/send-cloudwatch-alarms-to-slack.zip"
}

# Upload ZIP archive with lambda to S3 bucket
resource "aws_s3_bucket_object" "send_cloudwatch_alarms_to_slack" {
  bucket = aws_s3_bucket.lambda_bucket.id

  key    = "send-cloudwatch-alarms-to-slack.zip"
  source = data.archive_file.send_cloudwatch_alarms_to_slack.output_path

  etag = filemd5(data.archive_file.send_cloudwatch_alarms_to_slack.output_path)
}

# Create lambda function using ZIP archive from S3 bucket
resource "aws_lambda_function" "send_cloudwatch_alarms_to_slack" {
  function_name = "send-cloudwatch-alarms-to-slack"

  s3_bucket = aws_s3_bucket.lambda_bucket.id
  s3_key    = aws_s3_bucket_object.send_cloudwatch_alarms_to_slack.key

  runtime = "python3.9"
  handler = "lambda_function.lambda_handler"

  source_code_hash = data.archive_file.send_cloudwatch_alarms_to_slack.output_base64sha256

  role = aws_iam_role.send_cloudwatch_alarms_to_slack.arn

    environment {
    variables = {
      URL = "Testing"
    }
  }
}

# Create CloudWatch log group with 2 weeks retention policy
resource "aws_cloudwatch_log_group" "send_cloudwatch_alarms_to_slack" {
  name = "/aws/lambda/${aws_lambda_function.send_cloudwatch_alarms_to_slack.function_name}"

  retention_in_days = 14
}

# Grant access to SNS topic to invoke a lambda function
# Edit permissions to allow cross-account invocations from sns(dev,stage,prod)
resource "aws_lambda_permission" "sns_alarms" {
  statement_id  = "AllowExecutionFromSNSAlarms"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.send_cloudwatch_alarms_to_slack.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.slack_alerts.arn
}

# Trigger lambda function when a message is published to "alarms" topic
resource "aws_sns_topic_subscription" "alarms" {
  topic_arn = aws_sns_topic.slack_alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.send_cloudwatch_alarms_to_slack.arn
}

