import os
import time
import glob
import re
import socket
import imp

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

hubic_remote_dir = str(socket.gethostbyname(socket.gethostname()))

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
def SubDirPath (d):
	return filter(os.path.isdir, [os.path.join(d,f) for f in os.listdir(d)])

new_id = getnewid('backup')
# Create target directory if it is not present
# If statement checks whether the file directory exists
if not os.path.exists(target_dir):
	os.makedirs(target_dir)

if not os.path.exists(target_db_dir):
	os.makedirs(target_db_dir)

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

#Get a list of databases with :
database_list_command="mysql -u %s -p%s -h %s --silent -N -e 'show databases'" % (username, password, hostname)
for database in os.popen(database_list_command).readlines():
	database = database.strip()
	if database == 'information_schema':
		continue
	if database == 'performance_schema':
		continue
	filename = "%s/%s-%s-%s.sql" % (target_db_dir, now, database, str(new_id))
	database_list.append(filename)
	os.popen("mysqldump -u %s -p%s -h %s -e --opt -c %s | gzip -c > %s.gz" % (username, password, hostname, database, filename))

del_old_db_backup_command = "rm -f {0}/*-{1}.sql.gz".format(target_db_dir, new_id - day_store)
if os.system(del_old_db_backup_command) == 0:
	print("Successful del oldest backup database file")
else:
	print("del old Backup file FAILED on %s" % (del_old_db_backup_command))

### transfer to SFTP stuff ###

# onlyfiles = glob.glob(target_dir + "/" + "*.gz")
# for aa in onlyfiles:
# 	with pysftp.Connection(host=sftp_hostname, username=sftp_username, password=sftp_password, port=sftp_port) as sftp:
# 		with sftp.cd('backupvpsdime'):           # temporarily chdir to public
# 			try:
# 				sftp.put(aa)  # upload file to public/ on remote
# 			except Exception as e:
# 				print e
# 			print("transfer backup %s to SFTP OK" % (aa))
# onlyfiles_db = glob.glob(target_db_dir + "/"  + "*.gz")
# for bb in onlyfiles_db:
#         with pysftp.Connection(host=sftp_hostname, username=sftp_username, password=sftp_password, port=sftp_port) as sftp:
#                 with sftp.cd('backupvpsdime'):           # temporarily chdir to public
#                         try:
#                             	sftp.put(bb)  # upload file to public/ on remote
#                         except Exception as e:
#                                 print e
#                         print("transfer database to SFTP OK" % (bb))

### transfer to hubic ###

# refresh new token
#refesh_hubic_token = os.popen("python %shubic.py --refresh" % (script_path)).read()
#print refesh_hubic_token


# transfer code
for aa in code_list:
	upload_backup_code_to_hubic = os.popen("python %shubic.py --swift -- upload default/%s/ %s" % (script_path, hubic_remote_dir, aa)).read()
	print upload_backup_code_to_hubic

#transfer db
for bb in database_list:
	upload_backup_db_to_hubic = os.popen("python %shubic.py --swift -- upload default/%s/ %s.gz" % (script_path, hubic_remote_dir, bb)).read()
	print upload_backup_db_to_hubic

#delete old backup files
filelist_hubic = os.popen("python %shubic.py --swift -- list default" % (script_path)).read().split("\n")
for del_file in filelist_hubic[1:-1]:
	if re.search(r"%s.*\-%d\.(tar|sql)\.gz" % (hubic_remote_dir, new_id - day_remote_store), del_file):
		del_file_result = os.popen("python %shubic.py --swift -- delete default %s" % (script_path, del_file)).read()
		print del_file_result
