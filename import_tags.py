import boto.ec2, json, requests

#replace with Alert Logic API Key
API_KEY = 'REPLACE_WITH_YOUR_ALERT_LOGIC_API_KEY'
AWS_ACCESS_KEY = 'REPLACE_WITH_AWS_ACCESS'
AWS_SECRET_KEY ='REPLACE_WITH_AWS_SECRET'

API_KEYLIST_OF_AWS_INSTANCE_IDS = []
LIST_OF_INSTANCE_TAGS = []
NUMBER_OF_UPDATES = 0
NUMBER_OF_FAILED_UPDATES = 0

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
        TAG_UPDATE = json.dumps({"protectedhost": {"name": name}})
    else:
        jsonNewTag = '{"protectedhost":{"name":"'+str(name)+'","tags": ['+str(newTag)+']}}'
        TAG_UPDATE = json.loads(jsonNewTag)
        TAG_UPDATE = json.dumps(TAG_UPDATE)

    HEADERS = {'content-type': 'application/json'}
    URL = 'https://publicapi.alertlogic.net/api/tm/v1//protectedhosts/' + str(id)
    R = requests.post(URL, headers=HEADERS, auth=(API_KEY, ''),data = TAG_UPDATE)

    return R.status_code


#establish the AWS CLI connection and create lists of tags and instance IDs
conn = boto.ec2.connect_to_region('us-east-1',
   aws_access_key_id=AWS_ACCESS_KEY,
   aws_secret_access_key=AWS_SECRET_KEY)
reservations = conn.get_all_instances()
for res in reservations:
    for inst in res.instances:
        if 'Name' in inst.tags:
            API_KEYLIST_OF_AWS_INSTANCE_IDS.append(inst.id)
            LIST_OF_INSTANCE_TAGS.append(inst.tags)

#call Alert Logic sources API and get sources detail
HEADERS = {'content-type': 'application/json'}
PARAMS = {'search': 'i-'}
URL = 'https://publicapi.alertlogic.net/api/tm/v1//protectedhosts'
R = requests.get(URL, params=PARAMS, headers=HEADERS, auth=(API_KEY, ''))
output = R.json()

#proccess AWS instances looking for matches in Alert Logic (by instance ID)
listIndex = 0
for listIndex in range(len(API_KEYLIST_OF_AWS_INSTANCE_IDS)):
    if output["protectedhosts"]:
        index = 0
        for index in range(len(output["protectedhosts"])):
            if 'ec2_instance_id' in output["protectedhosts"][index]["protectedhost"]["metadata"]:
                if API_KEYLIST_OF_AWS_INSTANCE_IDS[listIndex] == output["protectedhosts"][index]["protectedhost"]["metadata"]["ec2_instance_id"]:
                    tempID = output["protectedhosts"][index]["protectedhost"]["id"]
                    # call update tags and store httpcode
                    httpCode = update_source_name(tempID,LIST_OF_INSTANCE_TAGS[listIndex])

                    if httpCode == 200:
                        NUMBER_OF_UPDATES = NUMBER_OF_UPDATES + 1
                    if httpCode == 400 or httpCode == 500:
                        NUMBER_OF_FAILED_UPDATES = NUMBER_OF_FAILED_UPDATES + 1



print ("Successfully updated %s record(s)" % NUMBER_OF_UPDATES)
print ("Unsuccessfully updated %s record(s)" % NUMBER_OF_FAILED_UPDATES)
