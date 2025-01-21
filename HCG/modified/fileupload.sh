#!/bin/bash
# shellcheck disable=SC2155

set -euo

debug_echo() {
    echo_message=${1:-""}
    echo >&2 "$echo_message"
}

banner_echo() {
    debug_echo
    debug_echo "***********************************************************"
    debug_echo "$1"
    debug_echo "***********************************************************"
    debug_echo
}

show_usage_exit_error() {
    echo >&2 "usage: $0 -filepath [Please provide path to the directory where the files to be uploaded are located]"
    exit 1
}


while [ $# -gt 0 ]
do
    case "$1" in
        -filepath) export filepath="$2"; shift;;
        -bucketname) export bucketname="$2"; shift;;
        -aws_access_key) export AWS_ACCESS_KEY_ID="$2"; shift;;
        -aws_secret_access_key) export AWS_SECRET_ACCESS_KEY="$2"; shift;;
        -aws_session_token) export AWS_SESSION_TOKEN="$2"; shift;;
        -*) show_usage_exit_error;;
        *)  break;; # terminate while loop
    esac
    shift
done

if aws --version; then
    banner_echo "Found existing installation of AWSCLI on this system"
 else 
    banner_echo "Unable to find AWSCLI on this system. Installing it now..."
    if ! python --version; then
        banner_echo "ERROR: Please install python on this system"
    fi
    sudo python -m pip install awscli boto3
    banner_echo "AWSCLI has been installed successfully"
fi


banner_echo "Uploading Files to your scratch bucket..."
aws s3 cp $filepath s3://$bucketname/ --recursive --sse --cli-read-timeout 0
banner_echo "Uploded Successfully"
