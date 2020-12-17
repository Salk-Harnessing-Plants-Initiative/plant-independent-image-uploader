# Installation
Ensure pipenv is installed on your computer. Then install the dependencies:
```
pipenv install
```
Install the [awscli](https://aws.amazon.com/cli/) and set your AWS credentials (our script uses the local `~/.aws/credentials` file):
```
aws configure
```
Copy the example config file, then fill out the settings:
```
cp config.yml.dst config.yml
```

# To run
```
pipenv run pythong main.py
```