resource "random_pet" "lambda_bucket_name" {
    prefix = "lambda"
    length = 2
  
}

resource "aws_s3_bucket" "lambda_bucket" {
    bucket = random_pet.lambda_bucket_name.id
    force_destroy = true
}