#!/bin/baash


rm user_status.txt
directory_id=$1
default_password="cJQS2pOugF1nQgq3vAD2"
default_team="your_team"

######## what it hipchat.txt  #####
# This is list of all users with format:
#  {hcs}user              | user@domain.com
##################

function generate_json() {
	if [ ! -z $2 ] ; then
		data="$1 $2"
	else
		data=$1
	fi
	username=$(awk 'BEGIN{FS = ":"}{print $1}' <<< $data)
	first_name=$(awk 'BEGIN{FS = ":"}{print $2}' <<< $data)
	last_name=$(awk 'BEGIN{FS = ":"}{print $3}' <<< $data | sed 's/\"//g')
	email=$(awk 'BEGIN{FS = ":"}{print $4}' <<< $data)
	u=$(awk -v e=$email '{if ($3 == e) {print substr($1,6)} }' hipchat.txt)
	

	echo "$username -> $first_name -> $last_name -> $email"
	echo "{\"type\": \"user\",\"user\": {\"username\": \"$username\",\"email\": \"$email\",\"password\": \"${default_password}\",\"nickname\": \"$username\",\"first_name\": \"$first_name\",\"last_name\": \"$last_name\",\"position\": \"Developer\",\"roles\": \"system_user\",\"locale\": \"en\",\"teams\": [{ \"name\": \"${default_team}\", \"roles\": \"team_user\", \"channels\": []}]}}," >> users_special.json
}

echo "[" > users_special.json

for i in $(mysql crowd -N -e "select id from cwd_user where directory_id = ${directory_id};"); do
	echo "get information about $i"
	generate_json $(mysql crowd -N -B -e "select SUBSTRING_INDEX(user_name, \"@\",1) as username, case first_name when \"\" then \"none\" ELSE first_name end  as f_name, case last_name when \"\" then \"none\" ELSE SUBSTRING_INDEX(last_name, \" \",1) end as l_name, email_address from cwd_user where id = $i" | awk 'BEGIN{FS = "\t"}{print $1":"$2":"$3":"$4}')
	mysql crowd -N -B -e "select SUBSTRING_INDEX(user_name, \"@\",1) as username, active from cwd_user where id = $i" >> user_status.txt
done

echo "]" >> users_special.json
