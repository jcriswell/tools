from __future__ import print_function
import boto3, json, requests
#API_KEY = 'REPLACE_WITH_YOUR_ALERT_LOGIC_API_KEY'

#request API call static Params
HEADERS = {'content-type': 'application/json'}
ALERT_LOGIC_API_URL = 'https://publicapi.alertlogic.net/api/tm/v1//protectedhosts/'
ALERT_LOGIC_LOG_API_URL = 'https://publicapi.alertlogic.net/api/lm/v1/sources/'


#Alert Logic source tag is a single value, while AWS has K:V based tags
#change to True if you want to capture both Key and Value, false is just value
USE_TAG_DELIMITER = True

#If set to true this is the char that will seperate the key and value in Alert Logic UI
#you can customize this char
DELIMITER = ":"
#format AWS tags for Alert Logic consumption and overrite tags on Alert Logic sources
#use the AWS instance "Name" for Alert Logic source name
def update_source_name(id, tags, API_KEY):
    name = ""
    newTag = ""
    for tag in tags:
        if tag['Key'] != 'Name':
            if newTag != "":
                newTag =  newTag + ','
            newTag =  newTag + '{"name":'
            if USE_TAG_DELIMITER:
                newTag = newTag + '"' + tag['Key'] + DELIMITER + tag['Value'] 
            else:
                newTag = newTag + '"' + tag['Key'] + " " + tag['Value']
            newTag = newTag + '"}'
        else:
        	name = str(tag['Value'])

    if newTag == "":
        tag_update = json.dumps({"protectedhost": {"name": name}})
    else:
        jsonNewTag = '{"protectedhost":{"name":"'+str(name)+'","tags": ['+str(newTag)+']}}'
        tag_update = json.loads(jsonNewTag)
        tag_update = json.dumps(tag_update)
    R = requests.post(ALERT_LOGIC_API_URL + str(id), headers=HEADERS, auth=(API_KEY,''),data = tag_update)
    return R.status_code
    
def get_log_source(instance_id, API_KEY):
    params = {'search': instance_id}
    R = requests.get(ALERT_LOGIC_LOG_API_URL, params=params, headers=HEADERS, auth=(API_KEY, ''))
    output = R.json()
    if output is None:
        print ("Recieved invalid JSON for query to Log API for instance-id: %s \n Requests Output: %s" % (instance_id, R.text))
        return None, False
    if output['sources']:
        if 'syslog' in output['sources'][0]:
            return output['sources'][0]['syslog']['id'], False
        elif 'eventlog' in output['sources'][0]:
            return output['sources'][0]['eventlog']['id'], True
    return None, False

def update_log_source_name(id, tags, isWin, API_KEY):
    name = ""
    newTag = ""
    for tag in tags:
        if tag['Key'] != 'Name':
            if newTag != "":
                newTag =  newTag + ','
            newTag =  newTag + '{"name":'
            if USE_TAG_DELIMITER:
                newTag = newTag + '"' + tag['Key'] + DELIMITER + tag['Value'] 
            else:
                newTag = newTag + '"' + tag['Key'] + " " + tag['Value']
            newTag = newTag + '"}'
        else:
        	name = str(tag['Value'])
    if not isWin: 
        if newTag == "":
            tag_update = json.dumps({"syslog": {"name": name, "method" : "agent"}})
        else:
            jsonNewTag = '{"syslog":{"name":"'+str(name)+'","method": "agent", "tags": ['+str(newTag)+']}}'
            tag_update = json.loads(jsonNewTag)
            tag_update = json.dumps(tag_update)
        R = requests.post(ALERT_LOGIC_LOG_API_URL + '/syslog/' + str(id), headers=HEADERS, auth=(API_KEY,''),data = tag_update)
        return R.status_code
        
    else:
        if newTag == "":
            tag_update = json.dumps({"eventlog": {"name": name}})
        else:
            jsonNewTag = '{"eventlog":{"name":"'+str(name)+'", "tags": ['+str(newTag)+']}}'
            tag_update = json.loads(jsonNewTag)
            tag_update = json.dumps(tag_update)
        R = requests.post(ALERT_LOGIC_LOG_API_URL + '/eventlog/' + str(id), headers=HEADERS, auth=(API_KEY,''),data = tag_update)
        return R.status_code
        

def lambda_handler(event, context):
	list_of_aws_instance_ids = []
	list_of_instance_tags = []
	accountNumbers = {}
	accountNumbers = event['accounts'].split(',')
	#externalIDs = {}
	#externalIDs = event['ExternalIds'].split(',')
	roleName = event['RoleName']
	all_accts_total_number_of_updates = 0
	all_accts_total_number_of_failed_updates = 0
	all_accts_total_number_of_log_updates = 0
	all_accts_total_number_of_failed_log_updates = 0
	for acctIndex in range(len(accountNumbers)):
		total_number_of_updates = 0
		total_number_of_failed_updates = 0
		total_number_of_log_updates = 0
		total_number_of_failed_log_updates = 0
		number_of_updates = 0
		number_of_failed_updates = 0
		number_of_log_updates = 0
		number_of_failed_log_updates = 0
		STSclient = boto3.client('sts')
		assumedRole = STSclient.assume_role(
			RoleArn = "arn:aws:iam::"+accountNumbers[acctIndex]+":role/"+roleName,
			RoleSessionName = 'ImportTags',
			DurationSeconds = 900
		)
		
		print("Begining tag import for account:%s" % accountNumbers[acctIndex])
		client = boto3.client('ec2', aws_access_key_id=assumedRole['Credentials']['AccessKeyId'], aws_secret_access_key=assumedRole['Credentials']['SecretAccessKey'], aws_session_token=assumedRole['Credentials']['SessionToken'])
		regions = client.describe_regions()
		for region in regions['Regions']:
			list_of_aws_instance_ids = []
			list_of_instance_tags = []
			number_of_updates = 0
			number_of_failed_updates = 0
			number_of_log_updates = 0
			number_of_failed_log_updates = 0
			client = boto3.client('ec2', region_name=region['RegionName'],aws_access_key_id=assumedRole['Credentials']['AccessKeyId'], aws_secret_access_key=assumedRole['Credentials']['SecretAccessKey'], aws_session_token=assumedRole['Credentials']['SessionToken'])
			reservations = client.describe_instances()
			print("Importing tags from region: %s" % region['RegionName'])
			for res in reservations['Reservations']:
			    for inst in res['Instances']:
			        if 'Tags' in inst.keys():
			        	list_of_aws_instance_ids.append(str(inst['InstanceId']))
			        	list_of_instance_tags.append(inst['Tags'])
			        	
			            
			            

			#call Alert Logic sources API and get sources detail
			params = {'search': 'i-'}
			if(len(list_of_aws_instance_ids) == 0 ):   #skip hitting our API if there's nothing in that region
				print("Skipping region %s for account %s as EC2 returned no instances in that region" % (region['RegionName'],accountNumbers[acctIndex]))
			else:
				R = requests.get(ALERT_LOGIC_API_URL, params=params, headers=HEADERS, auth=(event['apikey'], ''))
				output = R.json()
				
				#proccess AWS instances looking for matches in Alert Logic (by instance ID)
				listIndex = 0
				for listIndex in range(len(list_of_aws_instance_ids)):
				    if output["protectedhosts"]:
				        index = 0
				        for index in range(len(output["protectedhosts"])):

				            if 'ec2_instance_id' in output["protectedhosts"][index]["protectedhost"]["metadata"]:
				                if list_of_aws_instance_ids[listIndex] == output["protectedhosts"][index]["protectedhost"]["metadata"]["ec2_instance_id"]:
				                    tempID = output["protectedhosts"][index]["protectedhost"]["id"]
				                     #get corresponding log sources ID for the instance
				                    logID, isWin = get_log_source(output["protectedhosts"][index]["protectedhost"]["metadata"]["ec2_instance_id"],event['apikey'])
				                    # call update tags and store httpcode
				                    httpCode = update_source_name(tempID,list_of_instance_tags[listIndex],event['apikey'])
				                    # call update to sources DB for LM
				                    if logID is not None:
				                        httpCodeLog = update_log_source_name(logID, list_of_instance_tags[listIndex], isWin,event['apikey'])
				                    if httpCode == 200:
				                        number_of_updates = number_of_updates + 1
				                    if httpCode == 400 or httpCode == 500:
				                        number_of_failed_updates = number_of_failed_updates + 1
				                        print ("Update of Instance: %s using Protected Host ID: %s failed with return code: %s" % (output["protectedhosts"][index]["protectedhost"]["metadata"]["ec2_instance_id"], tempID, str(httpCode)))
				                    if httpCodeLog == 200:
				                        number_of_log_updates = number_of_log_updates + 1
				                    if httpCodeLog == 400 or httpCodeLog == 500:
				                        number_of_failed_updates = number_of_failed_updates + 1
				                        print ("Update of Instance: %s using Log Source ID: %s failed with return code: %s" % (output["protectedhosts"][index]["protectedhost"]["metadata"]["ec2_instance_id"], logID, str(httpCode)))
				                    
				                    
				                   



				print ("Successfully updated %s record(s) in region %s" % (number_of_updates,region['RegionName']))
				total_number_of_updates += number_of_updates
				total_number_of_failed_updates  += number_of_failed_updates 
				total_number_of_log_updates += number_of_log_updates 
				total_number_of_failed_log_updates += number_of_failed_log_updates
				all_accts_total_number_of_updates += number_of_updates
				all_accts_total_number_of_failed_updates += number_of_failed_updates
				all_accts_total_number_of_log_updates += number_of_log_updates
				all_accts_total_number_of_failed_log_updates += number_of_failed_log_updates
				number_of_updates = 0
				number_of_failed_updates = 0
				number_of_log_updates = 0
				number_of_failed_log_updates = 0
		print("Finished updating tags in account %s.  Total protected hosts updated: %s  Total Log Sources updated: %s  Number of Protected Host failures: %s   Number of Log Source failures:%s" % (accountNumbers[acctIndex], total_number_of_updates,total_number_of_log_updates,total_number_of_failed_updates,total_number_of_failed_log_updates))
	return "Successfully updated " + str(all_accts_total_number_of_updates ) + " protectedhosts and " + str(all_accts_total_number_of_log_updates) + " log sources. " + str(all_accts_total_number_of_failed_updates) + " failed protectedhosts and " + str(all_accts_total_number_of_failed_log_updates) + " failed log sources across all accounts"


