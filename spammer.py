from __future__ import print_function
import httplib2
import os
import base64

from email.mime.text import MIMEText
import time
from socket import error as SocketError

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
# SCOPES = 'https://www.googleapis.com/auth/gmail'
SCOPES = 'https://mail.google.com/'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Spammer'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'spammer.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def set_service():
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    return service


def get_thread_id(service, sender=None, subject=None):
    q = ""
    if sender:
        q = q+"from:{} ".format(sender)
    if subject:
        q = q+"subject:{} ".format(subject)

    threads_response = service.users().threads().list(userId='me',q=q).execute()
    num_threads = threads_response['resultSizeEstimate']
    threads = threads_response['threads']

    if num_threads != 1:
        print("Got {} threads. Help me select which thread you want to reply to!".format(num_threads))
        threads = threads_response['threads']
        for t in threads:
            print("ID:{} | Snippet:{}".format(t['id'], t['snippet']))
        thread_id = raw_input("Enter ID of the thread you want to reply to: ")
        return thread_id
    else:
        # print("\n\nGot the following thread. Initiating reply in 10 seconds. Abort if wrong thread selected\n\n")
        print("\n\nGot the following thread\n\n")
        print(threads[0]['snippet'])
        # time.sleep(10)
        return threads[0]['id']


def create_message(subject, to, sender, thread_id):
    message_file = raw_input("Enter complete file name with address (eg: ./reply.txt) containing your reply: ")
    with open(message_file, "r") as fp:
        message_text = fp.read()

    print("Message found: \n{}".format(message_text))
    raw_message = MIMEText(message_text)
    raw_message['Subject'] = subject
    raw_message['To'] = to
    raw_message['From'] = sender

    raw = base64.urlsafe_b64encode(raw_message.as_string())

    message = {'message': {'raw': raw, 'threadId': thread_id}}
    return message


def create_draft(service, message):
    draft = service.users().drafts().create(userId='me', body=message).execute()
    return draft


def get_thread_time_stamp(service, thread_id):
    try:
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
    except SocketError as e:
        print("Socket Error. Tryinh again... Mostly succeeds")
        time.sleep(4)
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
    
    last_message = thread['messages'][-1]
    for dic in last_message['payload']['headers']:
        if dic['name'] == 'Date':
            time_stamp = dic['value']
    return time_stamp


def log_last_message_time(service, thread_id, subject, sender):
    time_stamp = get_thread_time_stamp(service, thread_id)    

    print("Logging time of last message from thread: {}".format(time_stamp))
    with open("./{}_{}.txt".format(subject, sender), "a") as fp:
        fp.write(time_stamp+"\n")


def start_spam(service, message, thread_id):
    interval = int(raw_input("Enter time in seconds between spams: "))

    while True:
        print("Sending spam now")

        draft = create_draft(service, message)
        # print("Draft created. ID: {}".format(draft['id']))
        
        print("Sending spam in 20 seconds")
        time.sleep(20)
        draft_id = draft['id']
        sent = service.users().drafts().send(userId='me', body={'id':draft_id}).execute()
        
        time_stamp_old = get_thread_time_stamp(service, thread_id)
        print("Message sent at {}".format(time_stamp_old))
        time.sleep(interval)
        time_stamp_new = get_thread_time_stamp(service, thread_id)
        
        if time_stamp_old != time_stamp_new:
            print("Found new message at {}. Stopping spam".format(time_stamp_new))
            break

def main():
    print("Hi, I am Spammer!!")
    print("Please enter the subject and sender to help me search the thread you want to reply to")
    subject = raw_input("Enter Subject: ")
    sender = raw_input("Enter Sender: ")

    service = set_service()

    user_info = service.users().getProfile(userId='me').execute()
    user_email = user_info['emailAddress']

    thread_id = get_thread_id(service, sender=sender, subject=subject)
    # log_last_message_time(service, thread_id, subject, sender)

    message = create_message(subject, sender, user_email, thread_id)
    # draft = create_draft(service, message)

    start_spam(service, message, thread_id)
    # draft_id = draft['id']
    # sent = service.users().drafts().send(userId='me', body={'id':draft_id}).execute()

if __name__ == '__main__':
    main()