import os
import time
import glob
import re
import socket
import imp
import requests

script_path = os.path.dirname(os.path.realpath(__file__)) + os.sep


def getVarFromFile(filename):
    f = open(filename)
    global rootpass
    rootpass = imp.load_source('data', '', f)
    f.close()


getVarFromFile('/home/vpssim.conf')

username = "root"
password = rootpass.mariadbpass
hostname = "localhost"

source = '/home'

target_dir = "/usr/backup/code"
target_db_dir = "/usr/backup/database"

your_ip = requests.get('http://ipecho.net/plain').text

day_store = 1
day_remote_store = 10

code_list = []
database_list = []

# Create variable called now to give current date and time.
now = time.strftime('%Y%m%d-%H%M%S')


def getnewid(filename):
    try:
        temp = open(script_path + 'temp_' + filename + '.txt', 'r+')
    except Exception:
        temp = open(script_path + 'temp_' + filename + '.txt', 'w+')
        temp.write('0')
        temp.seek(0)
    old_id = temp.readline()
    temp.seek(0)
    new_id = int(old_id) + 1
    temp.write(str(new_id))
    temp.close()
    return new_id


def SubDirPath(d):
    return filter(os.path.isdir, [os.path.join(d, f) for f in os.listdir(d)])


new_id = getnewid('backup')


########## BACKUP code #########

# Create target directory if it is not present
# If statement checks whether the file directory exists
if not os.path.exists(target_dir):
    os.makedirs(target_dir)

for folder in SubDirPath(source):
    target = target_dir + os.sep + now + "-" + folder.split("/")[-1] + "-" + str(new_id) + ".tar.gz"
    code_list.append(target)
    # 5. We use the zip command to put the files in a zip archive.
    tar_command = "tar -zcPf {0} {1}".format(target, folder)
    if os.system(tar_command) == 0:
        print "Successful backup to", target
    else:
        print "Backup %s FAILED" % (folder.split("/")[-1])

del_old_backup_command = "rm -f {0}/*-{1}.tar.gz".format(target_dir, new_id - day_store)
if os.system(del_old_backup_command) == 0:
    print("Successful del oldest backup code file")
else:
    print("del old Backup file FAILED on %s" % (del_old_backup_command))

########## BACKUP DATABASE #########

# If statement checks whether the file directory exists
if not os.path.exists(target_db_dir):
    os.mkdir(target_db_dir)

# Get a list of databases with :
database_list_command = "mysql -u %s -p%s -h %s --silent -N -e 'show databases'" % (username, password, hostname)
for database in os.popen(database_list_command).readlines():
    database = database.strip()
    if database == 'information_schema':
        continue
    if database == 'performance_schema':
        continue
    filename = "%s/%s-%s-%s.sql" % (target_db_dir, now, database, str(new_id))
    database_list.append(filename)
    backupdb = os.popen("mysqldump -u %s -p%s -h %s -e --opt -c %s | gzip -c > %s.gz" % (
        username, password, hostname, database, filename))
    print('backup db %s' % backupdb)

del_old_db_backup_command = "rm -f {0}/*-{1}.sql.gz".format(target_db_dir, new_id - day_store)
if os.system(del_old_db_backup_command) == 0:
    print("Successful del oldest backup database file")
else:
    print("del old Backup file FAILED on %s" % (del_old_db_backup_command))

from pydrive.auth import GoogleAuth

gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication

from pydrive.drive import GoogleDrive

drive = GoogleDrive(gauth)


def uploadtoggd(gpath, fname, fpath):
    id = None

    file_list = drive.ListFile({'q': "'0B7MrJkoRADbVdWtlQXJpVm5TQkE' in parents and trashed=false"}).GetList()
    for file1 in file_list:
        if file1['title'] == gpath:
            id = file1['id']
            print('found folder %s - id:%s' % (gpath, file1['id']))
    if not id:
        print('create folder %s' % gpath)
        file1 = drive.CreateFile({'title': gpath,
                                    "parents":  [{"kind": "drive#fileLink", "id": '0B7MrJkoRADbVdWtlQXJpVm5TQkE'}],
                                    "mimeType": "application/vnd.google-apps.folder"})
        file1.Upload()
        id = file1['id']
        print('create folder successful id:%s' % id)

    file2 = drive.CreateFile({'title': fname,
                              "parents": [{"kind": "drive#fileLink", "id": id}]})
    file2.SetContentFile(fpath)
    result = file2.Upload()
    return result


# transfer code to ggd

for aa in code_list:
    gpath = your_ip
    fpath = aa
    fname = aa.split('/')[-1]
    print(uploadtoggd(gpath, fname, fpath))

# transfer db to s3
for bb in database_list:
    gpath = your_ip
    fpath = '%s.gz' % bb
    fname = '%s.gz' % bb.split('/')[-1]
    print(uploadtoggd(gpath, fname, fpath))
