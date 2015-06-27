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
sftp_port = sftpinfo[6].rstrip('\n')

source = '/home'

target_dir = "/usr/backup/code"
target_db_dir = "/usr/backup/database"

day_store = 3

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
		print "Backup FAILED"

del_old_backup_command = "rm -f {0}/*-{1}.tar.gz".format(target_dir, new_id - day_store)
if os.system(del_old_backup_command) == 0:
	print("Successful del oldest backup file")
else:
	print("del old Backup file FAILED")

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
	print("del old Backup file FAILED")

### transfer to SFTP stuff ###

onlyfiles = glob.glob(target_dir + "/" + "*.gz")
for aa in onlyfiles:
	with pysftp.Connection(host=sftp_hostname, username=sftp_username, password=sftp_password, port=sftp_port) as sftp:
		with sftp.cd('backupvpsdime'):           # temporarily chdir to public
			try:
				sftp.put(aa)  # upload file to public/ on remote
			except Exception as e:
				print e
			print("transfer backup code to SFTP OK")
onlyfiles_db = glob.glob(target_db_dir + "/"  + "*.gz")
for bb in onlyfiles_db:
        with pysftp.Connection(host=sftp_hostname, username=sftp_username, password=sftp_password, port=sftp_port) as sftp:
                with sftp.cd('backupvpsdime'):           # temporarily chdir to public
                        try:
                            	sftp.put(bb)  # upload file to public/ on remote
                        except Exception as e:
                                print e
                        print("transfer database to SFTP OK")
