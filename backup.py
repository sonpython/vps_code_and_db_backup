import os
import time
import glob
import pysftp

sftpinfofile = open('sftpinfo.txt', 'r')
sftpinfo = list(sftpinfofile)

username = sftpinfo[0].rstrip('\n')
password = sftpinfo[1].rstrip('\n')
hostname = sftpinfo[2].rstrip('\n')

sftp_hostname = sftpinfo[3].rstrip('\n')
sftp_username = sftpinfo[4].rstrip('\n')
sftp_password = sftpinfo[5].rstrip('\n')
sftp_port = int(sftpinfo[6].rstrip('\n'))

source = '/home'

target_dir = "/usr/backup/code"
target_db_dir = "/usr/backup/database"

hubic_remote_dir = "backupvpsdime"

day_store = 3
day_remote_store = 1

# Create variable called now to give current date and time.
now = time.strftime('%Y%m%d-%H%M%S')

def getnewid(filename):
	try:
		temp = open('temp_' + filename + '.txt', 'r+')
	except Exception:
		temp = open('temp_' + filename + '.txt', 'w+')
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
	os.mkdir(target_dir)

for folder in SubDirPath(source):
	target = target_dir + os.sep + now + "-" + folder.split("/")[-1] + "-" + str(new_id) + ".tar.gz"
	# 5. We use the zip command to put the files in a zip archive.
	tar_command = "tar -zcPf {0} {1}".format(target, folder)
	if os.system(tar_command) == 0:
		print "Successful backup to", target
	else:
		print "Backup %s FAILED" % (folder.split("/")[-1])

del_old_backup_command = "rm -f {0}/*-{1}.tar.gz".format(target_dir, new_id - day_store)
if os.system(del_old_backup_command) == 0:
	print("Successful del oldest backup file")
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
	os.popen("mysqldump -u %s -p%s -h %s -e --opt -c %s | gzip -c > %s.gz" % (username, password, hostname, database, filename))

del_old_db_backup_command = "rm -f {0}/*-{1}.sql.gz".format(target_db_dir, new_id - day_store)
if os.system(del_old_backup_command) == 0:
	print("Successful del oldest backup file")
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

refesh_hubic_token = os.popen("hubic.py --refresh").read()
print refesh_hubic_token
upload_backup_to_hubic = os.popen("python hubic.py --swift -- upload default/%s/ /usr/backup/*" % (hubic_remote_dir)).read()
print upload_backup_to_hubic

filelist_hubic = os.popen("python hubic.py --swift -- list default").read().split("\n")
for del_file in filelist_hubic[1:-1]:
        if re.search(r'.*\-%d\.tar\.gz' % (new_id - day_remote_store), del_file):
        	del_file_result = os.popen("python hubic.py --swift -- delete default %s" % (del_file)).read()
        	print del_file_result
