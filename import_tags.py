import boto.ec2, json, requests

#replace with Alert Logic API Key
API_KEY = 'REPLACE_WITH_YOUR_ALERT_LOGIC_API_KEY'
AWS_ACCESS_KEY = 'REPLACE_WITH_AWS_ACCESS'
AWS_SECRET_KEY ='REPLACE_WITH_AWS_SECRET'

#request API call static Params
HEADERS = {'content-type': 'application/json'}
ALERT_LOGIC_API_URL = 'https://publicapi.alertlogic.net/api/tm/v1//protectedhosts/'
ALERT_LOGIC_LOG_API_URL = 'https://publicapi.alertlogic.net/api/lm/v1/sources/'
list_of_aws_instance_ids = []
list_of_instance_tags = []
number_of_updates = 0
number_of_failed_updates = 0
number_of_log_updates = 0
number_of_failed_log_updates = 0
#Alert Logic source tag is a single value, while AWS has K:V based tags
#change to True if you want to capture both Key and Value, false is just value
USE_TAG_DELIMITER = False

#If set to true this is the char that will seperate the key and value in Alert Logic UI
#you can customize this char
DELIMITER = " | "


#format AWS tags for Alert Logic consumption and overrite tags on Alert Logic sources
#use the AWS instance "Name" for Alert Logic source name
def update_source_name(id, tags):
    name = tags['Name']
    newTag = ""
    for tag in tags:
        if tag != 'Name':
            if newTag != "":
                newTag =  newTag + ','
            newTag =  newTag + '{"name":'
            if USE_TAG_DELIMITER:
                newTag = newTag + '"' + tag + DELIMITER + tags[tag]  #this gets the key and the value
            else:
                newTag = newTag + '"' + tags[tag]
            newTag = newTag + '"}'

    if newTag == "":
        tag_update = json.dumps({"protectedhost": {"name": name}})
    else:
        jsonNewTag = '{"protectedhost":{"name":"'+str(name)+'","tags": ['+str(newTag)+']}}'
        tag_update = json.loads(jsonNewTag)
        tag_update = json.dumps(tag_update)



    R = requests.post(ALERT_LOGIC_API_URL + str(id), headers=HEADERS, auth=(API_KEY,''),data = tag_update)

    return R.status_code

def get_log_source(instance_id):
    params = {'search': instance_id}
    R = requests.get(ALERT_LOGIC_LOG_API_URL, params=params, headers=HEADERS, auth=(API_KEY, ''))
    output = R.json()
    if output['sources']:
        return output['sources'][0]['syslog']['id']
    return None

def update_log_source_name(id, tags):
    name = tags['Name']
    newTag = ""
    for tag in tags:
        if tag != 'Name':
            if newTag != "":
                newTag =  newTag + ','
            newTag =  newTag + '{"name":'
            if USE_TAG_DELIMITER:
                newTag = newTag + '"' + tag + DELIMITER + tags[tag]  #this gets the key and the value
            else:
                newTag = newTag + '"' + tags[tag]
            newTag = newTag + '"}'

    if newTag == "":
        tag_update = json.dumps({"syslog": {"name": name, "method" : "agent"}})
    else:
        jsonNewTag = '{"syslog":{"name":"'+str(name)+'","method": "agent", "tags": ['+str(newTag)+']}}'
        tag_update = json.loads(jsonNewTag)
        tag_update = json.dumps(tag_update)
    R = requests.post(ALERT_LOGIC_LOG_API_URL + '/syslog/' + str(id), headers=HEADERS, auth=(API_KEY,''),data = tag_update)
    return R.status_code

#establish the AWS CLI connection and create lists of tags and instance IDs
conn = boto.ec2.connect_to_region('us-east-1',
   aws_access_key_id=AWS_ACCESS_KEY,
   aws_secret_access_key=AWS_SECRET_KEY)
reservations = conn.get_all_instances()
for res in reservations:
    for inst in res.instances:
        if 'Name' in inst.tags:
            list_of_aws_instance_ids.append(inst.id)
            list_of_instance_tags.append(inst.tags)

#call Alert Logic sources API and get sources detail
params = {'search': 'i-'}
R = requests.get(ALERT_LOGIC_API_URL, params=params, headers=HEADERS, auth=(API_KEY, ''))
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
                    # call update tags and store httpcode
                    httpCode = update_source_name(tempID,list_of_instance_tags[listIndex])
                    #get corresponding log sources ID for the instance
                    logID = get_log_source(output["protectedhosts"][index]["protectedhost"]["metadata"]["ec2_instance_id"])
                    # call update to sources DB for LM
                    if logID is not None:
                        httpCodeLog = update_log_source_name(logID, list_of_instance_tags[listIndex])
                    if httpCode == 200:
                        number_of_updates = number_of_updates + 1
                    if httpCode == 400 or httpCode == 500:
                        number_of_failed_updates = number_of_failed_updates + 1
                    if httpCodeLog == 200:
                        number_of_log_updates = number_of_log_updates + 1
                    if httpCodeLog == 400 or httpCodeLog == 500:
                        number_of_failed_updates = number_of_failed_updates + 1
                    
                    
                   
print ("Successfully updated %s record(s)" % number_of_updates)
print ("Unsuccessfully updated %s record(s)" % number_of_failed_updates)
print ("Successfully updated %s log sources(s)" % number_of_updates)
print ("Unsuccessfully updated %s log sources(s)" % number_of_failed_updates)