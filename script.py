import itertools
from pathlib import Path
import sys
import threading
import time
from input_parsers import get_credentials_input, verify_sg_input
from typing import List, Union
import boto3
import csv
import logging
from datetime import datetime

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(message)s')

session = get_credentials_input()
region = session.region_name


def route_table_url(
    rtb_id): return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#RouteTableDetails:RouteTableId={rtb_id}"


def ec2_url(
    ec2_id): return f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#InstanceDetails:instanceId={ec2_id}"


def elb_url(
    elb_name): return f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#LoadBalancers:search={elb_name};sort=loadBalancerName"


def lambda_url(lambda_name):
    return f"https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions?fo=and&k0=functionName&o0=%3D&v0={lambda_name}"


def eks_url(eks_name):
    return f"https://{region}.console.aws.amazon.com/eks/home?region={region}#/clusters/{eks_name}"


def asg_url(asg_name):
    return f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#AutoScalingGroupDetails:id={asg_name};view=details"


def rds_url(rds_name):
    return f"https://{region}.console.aws.amazon.com/rds/home?region={region}#database:id={rds_name};is-cluster=false"


def vpc_endpoint_url(vpc_endpoint_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#Endpoints:search={vpc_endpoint_id}"


def nat_gateway_url(nat_gateway_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#NatGateways:search={nat_gateway_id}"


def vpgw_url(vpg_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#VpnGateways:VpnGatewayId={vpg_id}"


def eni_url(eni_id):
    return f"https://{region}.console.aws.amazon.com/ec2/home?region={region}#NIC:v=3;networkInterfaceId={eni_id}"


def acl_url(acl_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#acls:networkAclId={acl_id}"


def igw_url(igw_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#igws:internetGatewayId={igw_id}"


def route_table_url(route_table_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#RouteTables:routeTableId={route_table_id}"


def subnet_url(subnet_id):
    return f"https://{region}.console.aws.amazon.com/vpc/home?region={region}#subnets:SubnetId={subnet_id}"


new_file = Path(f"./{datetime.today().strftime('%Y-%m-%d')}.csv")
new_file.touch(exist_ok=True)
output_file = open(new_file, 'w')
writer = csv.writer(output_file)
writer.writerow(["Service", "ID", "Link"])

ec2_client = session.client("ec2")
elbV2_client = session.client('elbv2')
elb_client = session.client('elb')
lambda_client = session.client('lambda')
eks_client = session.client('eks')
asg_client = session.client('autoscaling')
rds_client = session.client('rds')
# ec2 = session.resource('ec2')


def get_and_verify_sg_input() -> Union[str, List[str], None]:
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


def get_enis_of_sg(sg_id: str) -> List[str]:
    response = session.client('ec2').describe_network_interfaces(
        Filters=[
            dict(Name='group-id', Values=sg_id)
        ]
    )
    return [eni["NetworkInterfaceId"] for eni in response["NetworkInterfaces"]]


def get_vpc_of_sgs(sg_ids: Union[str, List[str]]) -> List[str]:
    sg_id_filter = []
    if isinstance(sg_ids, list):
        sg_id_filter.extend(sg_ids)
    else:
        sg_id_filter.append(sg_ids)

    response = session.client('ec2').describe_network_interfaces(
        Filters=[dict(Name='group-id', Values=sg_id_filter)])

    vpcs = [eni["VpcId"] for eni in response["NetworkInterfaces"]]
    return list(set(vpcs))


def describe_network_interface(security_group_id: List[str]):
    print(get_enis_of_sg(security_group_id))


def vpc_in_region(vpc_id):
    """
    Describes one or more of your VPCs.
    """
    vpc_exists = False
    try:
        vpcs = list(ec2_client.vpcs.filter(Filters=[]))
    except boto3.exceptions.ClientError as e:
        logger.warning(e.response['Error']['Message'])
        exit()
    for vpc in vpcs:
        writer.writerow(["VPC", vpc.id, vpc_endpoint_url(vpc.id)])
        if vpc.id == vpc_id:
            vpc_exists = True

    return vpc_exists


def describe_asgs(vpc_ids, sg_ids):
    asgs = asg_client.describe_auto_scaling_groups()['AutoScalingGroups']
    for asg in asgs:
        asg_name = asg['AutoScalingGroupName']
        if asg_in_vpc(asg, vpc_ids, sg_ids):
            writer.writerow(["ASG", asg_name, asg_url(asg_name)])

    return


def asg_in_vpc(asg, vpc_ids, sg_ids):
    subnets_list = asg['VPCZoneIdentifier'].split(',')
    for subnet in subnets_list:
        try:
            sub_description = ec2_client.describe_subnets(SubnetIds=[subnet])[
                'Subnets']
            if sub_description[0]['VpcId'] in vpc_ids:
                return True
        except boto3.exceptions.ClientError:
            pass

    return False


def describe_ekss(vpc_ids, sg_ids):
    ekss = eks_client.list_clusters()['clusters']

    for eks in ekss:
        eks_desc = eks_client.describe_cluster(name=eks)['cluster']
        if eks_desc['resourcesVpcConfig']['vpcId'] in vpc_ids:
            writer.writerow(
                ["EKS", eks_desc["name"], eks_url(eks_desc["name"])])

    return


def describe_ec2s(vpc_ids, sg_ids):
    waiter = ec2_client.get_waiter('instance_terminated')
    reservations = ec2_client.describe_instances(Filters=[{"Name": "vpc-id",
                                                           "Values": vpc_ids}])['Reservations']

    # Get a list of ec2s
    ec2s = [ec2['InstanceId']
            for reservation in reservations for ec2 in reservation['Instances']]

    for ec2 in ec2s:
        writer.writerow(["EC2", ec2, ec2_url(ec2)])

    return


def describe_lambdas(vpc_ids, sg_ids):
    lmbds = lambda_client.list_functions()['Functions']

    lambdas_list = [lmbd['FunctionName'] for lmbd in lmbds
                    if 'VpcConfig' in lmbd and lmbd['VpcConfig']['VpcId'] in vpc_ids]

    for lmbda in lambdas_list:
        writer.writerow(["Lambda", lmbda, lambda_url(lmbda)])

    return


def describe_rdss(vpc_ids, sg_ids):
    rdss = rds_client.describe_db_instances()['DBInstances']

    rdsss_list = [rds['DBInstanceIdentifier']
                  for rds in rdss if rds['DBSubnetGroup']['VpcId'] in vpc_ids]

    for rds in rdsss_list:
        writer.writerow(["RDS", rds, rds_url(rds)])

    return


def describe_elbs(vpc_ids, sg_ids):
    elbs = elb_client.describe_load_balancers()['LoadBalancerDescriptions']

    elbs = [elb['LoadBalancerName'] for elb in elbs if elb['VPCId'] in vpc_ids]

    for elb in elbs:
        writer.writerow(["Classic ELB", elb, elb_url(elb)])

    return


def describe_elbsV2(vpc_ids, sg_ids):
    elbs = elbV2_client.describe_load_balancers()['LoadBalancers']

    elbs_list = [elb['LoadBalancerName']
                 for elb in elbs if elb['VpcId'] in vpc_ids]

    for elb in elbs_list:
        writer.writerow(["ELB V2", elb, elb_url(elb)])

    return


def describe_nats(vpc_ids, sg_ids):
    nats = ec2_client.describe_nat_gateways(Filters=[{"Name": "vpc-id",
                                                      "Values": vpc_ids}])['NatGateways']

    nats = [nat['NatGatewayId'] for nat in nats]

    for nat in nats:
        writer.writerow(["NAT GW", nat, nat_gateway_url(nat)])

    return


def describe_enis(vpc_ids, sg_ids):
    enis = ec2_client.describe_network_interfaces(
        Filters=[{"Name": "vpc-id", "Values": vpc_ids}])['NetworkInterfaces']

    # Get a list of enis
    enis = [eni['NetworkInterfaceId'] for eni in enis]

    for eni in enis:
        writer.writerow(["ENI", eni, eni_url(eni)])

    return


def describe_igws(vpc_ids, sg_ids):
    """
    Describe the internet gateway
    """

    # Get list of dicts
    igws = ec2_client.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id",
                  "Values": vpc_ids}])['InternetGateways']

    igws = [igw['InternetGatewayId'] for igw in igws]

    for igw in igws:
        writer.writerow(["IGW", igw, igw_url(igw)])

    return


def describe_vpgws(vpc_ids, sg_ids):
    """
    Describe the virtual private gateway
    """

    # Get list of dicts
    vpgws = ec2_client.describe_vpn_gateways(
        Filters=[{"Name": "attachment.vpc-id",
                  "Values": vpc_ids}])['VpnGateways']

    vpgws = [vpgw['VpnGatewayId'] for vpgw in vpgws]

    for vpgw in vpgws:
        writer.writerow(["VPGW", vpgw, vpgw_url(vpgw)])

    return


def describe_subnets(vpc_ids, sg_ids):
    # Get list of dicts of metadata
    subnets = ec2_client.describe_subnets(Filters=[{"Name": "vpc-id",
                                                    "Values": vpc_ids}])['Subnets']

    # Get a list of subnets
    subnets = [subnet['SubnetId'] for subnet in subnets]

    for subnet in subnets:
        writer.writerow(["Subnet", subnet, subnet_url(subnet)])

    return


def describe_acls(vpc_ids, sg_ids):
    acls = ec2_client.describe_network_acls(Filters=[{"Name": "vpc-id",
                                                      "Values": vpc_ids}])['NetworkAcls']

    # Get a list of subnets
    acls = [acl['NetworkAclId'] for acl in acls]

    for acl in acls:
        writer.writerow(["Network ACL", acl, acl_url(acl)])

    return


def describe_rtbs(vpc_ids, sg_ids):
    rtbs = ec2_client.describe_route_tables(Filters=[{"Name": "vpc-id",
                                                      "Values": vpc_ids}])['RouteTables']
    # Get a list of Routing tables
    rtbs = [rtb['RouteTableId'] for rtb in rtbs]

    for rtb in rtbs:
        writer.writerow(["Route Table", rtb, route_table_url(rtb)])

    return


def describe_vpc_epts(vpc_ids, sg_ids):
    epts = ec2_client.describe_vpc_endpoints(Filters=[{"Name": "vpc-id",
                                                       "Values": vpc_ids}])['VpcEndpoints']

    # Get a list of Routing tables
    epts = [ept['VpcEndpointId'] for ept in epts]

    for ept in epts:
        writer.writerow(["VPC Endpoint", ept, vpc_endpoint_url(ept)])

    return


if __name__ == "__main__":
    done = False

    def animate():
        for c in itertools.cycle(['|', '/', '-', '\\']):
            if done:
                break
            sys.stdout.write('\r\tExecuting script ' + c)
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r\tCompleted!     ')

    sg_ids = get_and_verify_sg_input()

    print()
    t = threading.Thread(target=animate)
    t.start()

    vpc_ids = get_vpc_of_sgs(sg_ids)

    describe_ekss(vpc_ids, sg_ids)
    describe_asgs(vpc_ids, sg_ids)
    describe_rdss(vpc_ids, sg_ids)
    describe_ec2s(vpc_ids, sg_ids)
    describe_lambdas(vpc_ids, sg_ids)
    describe_elbs(vpc_ids, sg_ids)
    describe_elbsV2(vpc_ids, sg_ids)
    describe_nats(vpc_ids, sg_ids)
    describe_vpc_epts(vpc_ids, sg_ids)
    describe_igws(vpc_ids, sg_ids)
    describe_vpgws(vpc_ids, sg_ids)
    describe_enis(vpc_ids, sg_ids)
    describe_rtbs(vpc_ids, sg_ids)
    describe_acls(vpc_ids, sg_ids)
    describe_subnets(vpc_ids, sg_ids)

    output_file.close()
    done = True
