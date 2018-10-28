# Pinger - 24x7 website monitoring lambda

![Architecture](Images/24x7-website-monitoring-lambda.png/?raw=true "Architecture Logo")

This repository contains the Lambda function built with serverless application model(aka SAM) that monitors web URLs asynchronously, capture response times & response codes in cloud watch and enables slack notifications during 4XX & 5XX failures of the URLs and also a restoration notification once the service is restored.

## Pricing Estimation

Approx. AWS costs for lambda to monitor 10 URLs with the scheduled frequency of 5 mins. Kindly note that this is just an estimation. Actuals might differ and subject to the number of URLs that you add to monitor. Estimation is done through [Link](https://s3.amazonaws.com/lambda-tools/pricing-calculator.html)

![Pricing](Images/pricing.png/?raw=true "Pricing Info")

## Features

* Maintains the state of the URL
* Slack Notifications when web URLs response code are not equal to 200
* Slack Notifications, once the URL is back online
* Response times of the web URLs are shipped to cloud watch. You can optionally enable custom metrics and log aggregation to elastic search(optional, might incur additional costs).
* Cloudwatch Alarms(optional, might incur additional costs).
* Easy to adjust the monitoring scheduled frequency
* Easy to add and remove URLs by just adding/removing them from config file(config.yaml) available in this repository
* Very Low cost monitoring solution
* Easy to customize the source code and CI/CD solution on Jenkins is already in place.

## Comparison (vs Pingdom)

![Comparison](Images/comparison.png/?raw=true "Comparison")

Refer the wiki page for more detailed documentation. [go to wiki page](https://github.com/Servana/24x7-website-monitoring-lambda/wiki)