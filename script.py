import json
import traceback
from typing import List, Optional, Union
import boto3

from input_parsers import get_credentials_input, input_y_n, verify_sg_input
from helpers import filter_response


def start_session(aws_access_key_id: Optional[str] = None,
                  aws_secret_access_key: Optional[str] = None, profile_name: Optional[str] = None) -> boto3.Session:
    if aws_access_key_id is None and aws_secret_access_key is None:
        if profile_name is None:
            return boto3.Session()

        else:
            return boto3.Session(profile_name=profile_name)

    return boto3.Session(
        aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


def get_and_verify_sg_input(session: boto3.Session) -> Union[str, List[str], None]:
    security_group_input = input(
        "Input security group id [example: sg-140123123], if there are multiple, delimit with a comma [example: sg-140123123,sg-398138123,sg-3912931]: ")

    security_group_ids = []

    if security_group_input.find(',') != '-1':
        security_group_ids.extend(security_group_input.split(','))
        sg_input_valid = verify_sg_input(session, security_group_ids)

        if sg_input_valid:
            return security_group_ids

        else:
            print(
                f"One of the Security Group ID {security_group_ids} is invalid")

    else:
        security_group_ids.append(security_group_input)

    return security_group_ids


def generate_eni_link(eni_id: str, region: str) -> str:
    return f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#NetworkInterface:networkInterfaceId={eni_id}"


def describe_network_interface(session: boto3.Session, security_group_id: List[str]):
    response = session.client('ec2').describe_network_interfaces(
        Filters=[
            {
                'Name': 'group-id',
                'Values':
                    security_group_id
            },
        ],
    )

    response_fields = ['AvailabilityZone', 'Description', 'InterfaceType', 'NetworkInterfaceId', 'OwnerId',
                       'Status', 'VpcId']
    # available options: ['Attachment', 'AvailabilityZone', 'Description', 'Groups', 'InterfaceType', 'Ipv6Addresses', 'MacAddress', 'NetworkInterfaceId', 'OwnerId', 'PrivateIpAddress', 'PrivateIpAddresses', 'RequesterId', 'RequesterManaged', 'SourceDestCheck', 'Status', 'SubnetId', 'TagSet', 'VpcId', 'DenyAllIgwTraffic']
    # edit response_fields with fields that you want

    print(json.dumps(
        [dict(**filter_response(eni, response_fields), View=generate_eni_link(eni["NetworkInterfaceId"], boto3_session.region_name)) for eni in response["NetworkInterfaces"]], indent=4, default=str))


def find_enis(boto3_session: boto3.Session):
    sg_ids = get_and_verify_sg_input(boto3_session)
    describe_network_interface(boto3_session, sg_ids)

    go_again = input_y_n("Search for another?")

    while go_again:
        sg_ids = get_and_verify_sg_input(boto3_session)
        describe_network_interface(boto3_session, sg_ids)
        print()
        go_again = input_y_n("Search for another?")


if __name__ == "__main__":
    print("Running script to get attached ENI...")
    try:
        profile_name, aws_access_key_id, aws_secret_access_key = get_credentials_input()

        if aws_access_key_id is not None and aws_secret_access_key is not None:
            boto3_session = start_session(
                aws_access_key_id, aws_secret_access_key)

        else:
            boto3_session = start_session(profile_name=profile_name)

        find_enis(boto3_session)

    except Exception as e:
        traceback.print_exc()
        exit(0)
