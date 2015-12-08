# tools
scripts for using the alert logic API and AWS API


##import_tags.py

AWS Lambda Function that will import the tags from EC2 instances into Alert Logic.  The function will import tags from instances in all regions where instances are running.
The function takes an event in the format of:
{
  "apikey": "Your Alert Logic API Key",
}

The Lambda execution role required is:


{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:*"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Sid": "Stmt1448994484000",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "ec2:DescribeTags"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}

The Lambda function handler is: import_tags.lambda_handler

The timeout should be set too 5 minutes.

Because the Lambda function leverages the requests module you will need to create a ZIP file of the entire contents (including subdirectories) and upload either directly to Lambda or to an S3 bucket.

##import_tags_mutliaccount.py
Same as above except designed to run within a shared services account managing a number of other accounts.  The function will assume a role in the defined in the event for the accounts listed to perform the tag import across multiple AWS accounts.

The function takes an event in the format of:
{
  "apikey": "Your Alert Logic API Key",
  "accounts":"AWSAccount#1,AWSAccount#2,...,AWSAccount#N",
  "RoleName": "IAM Role Name"
}

Note the name of IAM role must be the same across each of the accounts.  The Lambda execution role required is:
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "sts:AssumeRole"
            ],
            "Resource": "arn:aws:iam::*:role/<IAM_ROLE_NAME>"
        }
    ]
}

Replacing <IAM_ROLE_NAME> with the name of the role specified in the RoleName parameter.


The Role being assumed needs the following permissions:

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1448994484000",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "ec2:DescribeTags"
            ],
            "Resource": [
                "*"
            ]
        }
    ]
}



The Lambda function handler is: import_tags_mutliaccount.lambda_handler

The timeut should be set to 5 minutes.  

Because the Lambda function leverages the requests module you will need to create a ZIP file of the entire contents (including subdirectories) and upload either directly to Lambda or to an S3 bucket.
