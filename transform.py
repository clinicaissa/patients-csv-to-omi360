import sys
import csv
import logging

# Constants
SRC_COL_DELIMITER="\t"
SRC_ROW_DELIMITER="\n"
DST_COL_DELIMITER="@|@"
DST_ROW_DELIMITER="¤"

# Config
logging.basicConfig(level=logging.INFO)

# Read arguments
args = sys.argv[1:]
if len(args) == 0:
	logging.error("Specify the file to transform")
	sys.exit(1)
file=args[0]
logging.info("Transforming file %s" % file)

# Read file
try:
	input=open(file, "r")
except Exception as e:
	logging.error("Unable to open file %s: %s", file, str(e))
reader = csv.reader(input, delimiter=SRC_COL_DELIMITER, quotechar='"')
input_lines=list(reader)
header=input_lines[0]
logging.info("Set first row as header")
logging.info("Found %d records", len(input_lines))
## Print headers
logging.info("Headers are:")
for i in range(len(header)):
	print("%02d: %s" % (i, header[i]))

# Transform
## 1. Split surnames
logging.info("1. Split surnames")
surnames_count=[0,0,0]
for i in range(1, len(input_lines)):
	line = input_lines[i]
	surnames=line[5]
	surnames_tuple=surnames.split(" ")
	first_surname=""
	second_surname=""
	# Two or more surnames
	if len(surnames_tuple) >= 2:
		first_surname=surnames_tuple[0]
		second_surname=" ".join(surnames_tuple[1:])
		surnames_count[2] += 1
	# One or less surnames
	elif len(surnames_tuple) == 1:
		first_surname=surnames_tuple[0]
		surnames_count[1] += 1
	# No surnames
	else:
		surnames_count[0] += 1
	#print(first_surname, "|", second_surname)
	# Append surnames split
	line = line[:5] + [first_surname, second_surname] + line[6:]
	#print(line)
	input_lines[i] = line
logging.info("   Found %d with 2+ surnames, %d with one and %d without any" %
	(surnames_count[2], surnames_count[1], surnames_count[0]))
## Append header line
header=header[:5] + ["Primer Apellido", "Segundo Apellido"] + header[6:]
## Print headers
logging.info("Headers are:")
for i in range(len(header)):
        print("%02d: %s" % (i, header[i]))
input_lines[0]=header
# 2. Modify fields
sex_count=[0,0,0]
logging.info("2. Modify fields format")
for i in range(1, len(input_lines)):
	## Obtain line
	line = input_lines[i]
	### Sex field
	sex = line[10]
	new_sex = "O"
	if sex == "H":
		new_sex = "M"
		sex_count[0] += 1
	elif sex == "M":
		new_sex = "F"
		sex_count[1] += 1
	else:
		sex_count[2] += 1
logging.info("   Found %d males, %d females and %d unidentified" % (
	sex_count[0], sex_count[1], sex_count[2]))
# 3. Order fields
logging.info("3. Moving columns")
ORDER=[22, 5, 6, 4, 0, 10]
# 4. Sample values
logging.info("4. Sample values")
for i in range(len(header)):
	print("%02d (%15s): %s" % (i, header[i], input_lines[1][i]))
