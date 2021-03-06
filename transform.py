#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Name: CSV of Patients to OMI360 transformation script
# Description: The script allows to transform an export of the current
# database of insurance policies owners and beneficiaries into the format
# required by Stacks.es OMI360 product. Requires the export in a delimited
# CSV of the owners and beneficiaries
#
# Usage: python transform.py <owners_file> <beneficiaries_file>
import sys
import os
import re
import pandas as pd
import numpy as np
import logging
import datetime
import fileinput

# Constants
CURRENT_DATE_NP = np.datetime64(datetime.datetime.now())
"""
Current date and time to detect past and future times
"""

# # Source parameters
SRC_COL_DELIMITER = "\t"
SRC_ROW_DELIMITER = "\n"
SRC_QUOTE_CHAR = "\""
SRC_BEN_COLS_DROP = [
    'FECHANACIMI',  # No longer used
    'FECHAINSCRI',  # No longer used
    'Empresa',      # All ones
]
SRC_BEN_COLS_RENAME = {
    "CENTRO": "CENTRO",
    "Nombre": "NOMBRE",
    "Sexo": "SEXO",
    "Fecha Nacimiento": "NACIMIENTO",
    "#": "NHC",
    "NIF": "DOCUMENTO",
    "Fecha Inscripcion": "FECHA_ALTA",
    "E.Mail": "EMAIL",
    "N.Poliza": "NUM_POLIZA"
}
SRC_BEN_COLS_DATETIME = ['Fecha Nacimiento', 'Fecha Inscripcion']

SRC_OWN_COLS_DATETIME = ['Fecha Alta', 'Fecha Baja']

# # # Parser
def SRC_DATE_PARSER(date):
    if pd.isnull(date):
        return date
    # Final date
    date = date.replace("/", "")
    # Correct date
    if len(date) != 6 or len(date) != 8:
        # Replace full years
        re.sub(r"19(\d{2})", r"\1", date)
    # Add slashes
    date = date[:2] + "/" + date[2:4] + "/" + date[4:]
    # Two-digit year
    if len(date) == 8 and re.match("^\d{2}/\d{2}/\d{2}$", date):
        parsed = pd.datetime.strptime(date, "%d/%m/%y")
    # Four-digit year
    if len(date) == 10:
        parsed = pd.datetime.strptime(date, "%d/%m/%Y")
    # Final result
    return parsed


# # # Transformations
def UNIFORM_NAMES(name):
    # Multiple spaces are not allowed
    name = re.sub(' +',' ', name).strip()
    # Uniform quotation
    name = name.replace('`', "'")
    # No space after quotation
    name = name.replace("' ", "")
    # Title
    name = name.title()
    # Replace prepositions
    name = name.replace(" Del", " del")
    name = name.replace(" De", " de")
    return name

def SRC_TRF_NOMBRE(nombre):
    return UNIFORM_NAMES(nombre) if isinstance(nombre, str) else nombre


def SRC_TRF_EMAIL(email):
    return email.lower() if isinstance(email, str) else email


def SRC_TRF_CENTRO(centro):
    return "MATARO-NOU"


def SRC_TRF_SEXO(sexo):
    return "M" if sexo == "H" else "F" if sexo == "M" else "O"


def SRC_TRF_NIF(nif):
    # Nulls
    if pd.isnull(nif):
        return nif
    # NIF correction
    return nif.strip().replace("-", "").replace(" ", "").upper()

def SRC_TRF_POBLACION(poblacion):
    if isinstance(poblacion, str):
        poblacion = UNIFORM_NAMES(poblacion)
        poblacion = poblacion.replace("Mataro", "Mataró")
    return poblacion

def SRC_TRF_CPOSTA(cposta):
    # Check is an integer
    if pd.isnull(cposta):
        return cposta
    try:
        cposta = int(cposta)
    except:
        return np.NaN
    return cposta


SRC_BEN_TRANSFORMATIONS = {
    "CENTRO": SRC_TRF_CENTRO,
    "Nombre": SRC_TRF_NOMBRE,
    "E.Mail": SRC_TRF_EMAIL,
    "Sexo": SRC_TRF_SEXO,
    "NIF": SRC_TRF_NIF
}

SRC_BEN_COLS_TYPES = {
    "CENTRO": "category",
    "Sexo": "category"
}

SRC_OWN_EXTRAS = {
    "DIRE": ("DIRECCION", SRC_TRF_POBLACION),
    "CPOSTA": ("POSTAL", SRC_TRF_CPOSTA),
    "POBLA": ("POBLACION", SRC_TRF_POBLACION),
    "PROVINNOM": ("PROVINCIA", SRC_TRF_NOMBRE),
}

SRC_OWN_COLS_TYPES = {
    "CPOSTA": "category",
    "PROVINNOM": "category",
    "POBLA": "category"
}

# # Destination parameters
DST_COL_DELIMITER = "@|@"
DST_TMP_DELIMITER = "\t"
DST_ROW_DELIMITER = "¤"
DST_QUOTE_CHAR = None
DST_COLS_MANDATORY = ['CENTRO', 'APELLIDO1', 'NOMBRE', 'NACIMIENTO', 'NHC']
DST_COLS_OUTPUT = \
    ["CENTRO", "APELLIDO1", "APELLIDO2", "NOMBRE", "NHC", "NACIMIENTO",
     "SEXO", "TIPO_DOCUMENTO", "DOCUMENTO", "DIRECCION", "POSTAL",
     "POBLACION", "PROVINCIA", "TELEFONO", "TMOVIL", "EMAIL",
     "COBERTURA", "NUM_POLIZA", "NUM_TARJETA", "NSS", "TIS", "OBSERVACIONES",
     "MEDICO", "ACTIVO", "FECHA_ALTA", "PAIS"]


# # # New columns transformations
def DST_COL_APELLIDO1(apellidos):
    return SRC_TRF_NOMBRE(apellidos.split()[0]) \
        if isinstance(apellidos, str) else None


def DST_COL_APELLIDO2(apellidos):
    return SRC_TRF_NOMBRE(" ".join(apellidos.split()[1:])) \
        if isinstance(apellidos, str) else None


def DST_COL_TIPO_DOCUMENTO(documento):
    return 1 if isinstance(documento, str) else np.NaN


def DST_COL_ACTIVO(fecha_baja):
    return "NO" if isinstance(fecha_baja, np.datetime64) \
        and fecha_baja > CURRENT_DATE_NP else "SI"


def DST_COL_TELEFONO(telf):
    telefono = np.NaN
    if isinstance(telf, str):
        telfs = telf.strip().replace(".", "").split()
        for telf in telfs:
            # 7-digit number, missing +93
            match = re.match("^\d{7}$", telf)
            if match is not None:
                telefono = int("93" + match.group(0))
                break
            # 9-digit number, non-starting per 6/7
            match = re.match("^\d{9}$", telf)
            if match is not None and telf[0] != "6" and telf[0] != "7":
                telefono = int(match.group(0))
                break
    return telefono


def DST_COL_TMOVIL(telf):
    telefono = np.NaN
    if isinstance(telf, str):
        telfs = telf.strip().replace(".", "").split()
        for telf in telfs:
            # 9-digit number, starting per 6/7
            match = re.match("^[67]\d{8}$", telf)
            if match is not None:
                telefono = int(match.group(0))
                break
    return telefono

DST_COLS_GENERATED = {
    "TIPO_DOCUMENTO": ("NIF", DST_COL_TIPO_DOCUMENTO),
    "APELLIDO1": ("Apellidos", DST_COL_APELLIDO1),
    "APELLIDO2": ("Apellidos", DST_COL_APELLIDO2),
    "TELEFONO": ("Telefono", DST_COL_TELEFONO),
    "TMOVIL": ("Telefono", DST_COL_TMOVIL),
    "ACTIVO": ("Fecha Baja", DST_COL_ACTIVO),
}

DST_COLS_TYPES = {
    "CENTRO": "category",
    "SEXO": "category",
    "TIPO_DOCUMENTO": "category"
}


# Config
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s][%(name)s][%(levelname)s] %(message)s"
)

# Read arguments
args = sys.argv[1:]
if len(args) < 2:
    logging.error("Specify the files to transform")
    logging.error(
        "Usage: python transform.py <beneficiaries_file> <owners_file>")
    sys.exit(1)
beneficiaries_file = args[0]
owners_file = args[1]
logging.info("Using file %s as beneficiaries" % beneficiaries_file)

# Read files
# # Input file
logging.info("Reading file %s" % beneficiaries_file)
patients = pd.read_table(
    beneficiaries_file,
    header=0,
    delimiter=SRC_COL_DELIMITER,
    quotechar=SRC_QUOTE_CHAR,
    parse_dates=SRC_BEN_COLS_DATETIME,
    date_parser=SRC_DATE_PARSER
)
logging.info(" - Set first row as header")
logging.info(" - Found %d records", len(patients))
logging.info(" - Headers are %s", patients.columns)

# Transform
logging.info("=== Applying transformations ===")
# # 1. Clean invalid columns
logging.info("1. CLEAN invalid columns")
logging.info("   Remove no-longer-used columns: %s", SRC_BEN_COLS_DROP)
patients = patients.drop(SRC_BEN_COLS_DROP, 1)
# # 2. Rename columns
logging.info("2. RENAME valid columns")
patients.rename(inplace=True, columns=SRC_BEN_COLS_RENAME)
logging.info("   Updated headers are %s", SRC_BEN_COLS_RENAME)
# # 3. Internal formatting
logging.info("3. READ COLUMNS format")
logging.info("   Columns %s are datetimes",
             list(map(SRC_BEN_COLS_RENAME.get, SRC_BEN_COLS_DATETIME)))
for col, dtype in SRC_BEN_COLS_TYPES.items():
    logging.info("   Column %s is type <%s>", col, dtype)
    patients[SRC_BEN_COLS_RENAME.get(col, col)] = \
        patients[SRC_BEN_COLS_RENAME.get(col, col)].astype(dtype)
# # 4. Extra columns
logging.info("4. ADDING new columns")
for col, creator in DST_COLS_GENERATED.items():
    src_col, creator = creator
    logging.info("   Creating column %s from column %s", col, src_col)
    # Apply creation transformation
    src_col = SRC_BEN_COLS_RENAME.get(src_col, src_col)
    new_col = patients[src_col].apply(creator)
    # Set type
    if col in DST_COLS_TYPES:
        new_col = new_col.astype(DST_COLS_TYPES[col])
    # New column details
    if isinstance(new_col.dtype, pd.core.dtypes.dtypes.CategoricalDtype):
        logging.info("   -> New categorical distribution:")
        lines = str(new_col.value_counts()).split("\n")
        for line in lines:
            logging.info("      %s", line)
    else:
        logging.info("    -> New column:")
        lines = str(new_col.describe()).split("\n")
        for line in lines:
            logging.info("      %s", line)
    # Append to dataframe
    patients[col] = new_col
# # 5. Format transformations
logging.info("5. APPLYING COLUMN transformations")
for col, transform in SRC_BEN_TRANSFORMATIONS.items():
    # Renaming
    col = SRC_BEN_COLS_RENAME.get(col, col)  # Not renamed maybe
    logging.info("   Transforming column %s", col)
    # Apply transformation
    old_col = patients[col]
    new_col = old_col.apply(transform)
    # Set type
    if col in SRC_BEN_COLS_TYPES:
        new_col = new_col.astype(SRC_BEN_COLS_TYPES[col])
    # Check distribution if categorical
    if isinstance(old_col.dtype, pd.core.dtypes.dtypes.CategoricalDtype):
        logging.info("   -> Old distribution:")
        lines = str(old_col.value_counts()).split("\n")
        for line in lines:
            logging.info("      %s", line)
    else:
        logging.info("    -> Old column:")
        lines = str(old_col.describe()).split("\n")
        for line in lines:
            logging.info("      %s", line)
    if isinstance(new_col.dtype, pd.core.dtypes.dtypes.CategoricalDtype):
        logging.info("   -> New distribution:")
        lines = str(new_col.value_counts()).split("\n")
        for line in lines:
            logging.info("      %s", line)
    else:
        logging.info("    -> New column:")
        lines = str(new_col.describe()).split("\n")
        for line in lines:
            logging.info("      %s", line)
    # Save transformation
    patients[col] = new_col

# # 6. Mix data
logging.info("6. ADD columns from owners file")
# Read files
# # Input file
logging.info("Using file %s as owners" % owners_file)
logging.info("Reading file %s" % owners_file)
owners = pd.read_table(
    owners_file,
    header=0,
    delimiter=SRC_COL_DELIMITER,
    quotechar=SRC_QUOTE_CHAR,
    parse_dates=SRC_OWN_COLS_DATETIME,
    date_parser=SRC_DATE_PARSER
)
logging.info(" - Set first row as header")
logging.info(" - Found %d records", len(owners))
logging.info(" - Headers are %s", owners.columns)

# Loop each owner and add its address
for index, owner in owners.iterrows():
    # Get number of policy
    poliza = owner["NPOLIZA"]
    # Generate new columns
    cols = []
    for col, extra in SRC_OWN_EXTRAS.items():
        # Get new name and value
        new_name, transformation = extra
        cols.append((new_name, transformation(owner[col])))
    # Append columns
    for col, val in cols:
        patients.loc[patients["NUM_POLIZA"] == poliza, col] = val

# # 7. Clean invalid rows
logging.info("7. CLEAN invalid rows")
logging.info("   Rows without %s", DST_COLS_MANDATORY)
# # # Null cleans
for col in DST_COLS_MANDATORY:
    patients = patients[pd.notnull(patients[col])]
logging.info("   -> Without nulls: %d records", len(patients))
# # # Invalid strings
for col in DST_COLS_MANDATORY:
    if patients[col].dtype == np.object:
        patients = patients[patients[col].map(len) > 0]
logging.info("   -> Without empty strings: %d records", len(patients))
# # 8. Write results
patients["POSTAL"] = patients["POSTAL"].fillna(0).astype(int)
logging.info("8. WRITING result")
logging.info("   ColDelimiter=%s | RowDelimiter=%s",
             DST_COL_DELIMITER, DST_ROW_DELIMITER)
logging.info("   Export columns: %s", DST_COLS_OUTPUT)
DST_FILE_NAME = ".".join(os.path.basename(beneficiaries_file).split(".")[:-1])
DST_FILE_EXT = os.path.basename(beneficiaries_file).split(".")[-1]
DST_FILE = DST_FILE_NAME + "_converted." + DST_FILE_EXT
logging.info("   Export name: %s", DST_FILE)
delimiter = DST_COL_DELIMITER
if len(DST_COL_DELIMITER) > 1:
    logging.info("Using temporary delimiter <%s>", DST_TMP_DELIMITER)
    delimiter = DST_TMP_DELIMITER
patients.to_csv(DST_FILE,
                index=False,
                columns=DST_COLS_OUTPUT,
                sep=delimiter,
                line_terminator=DST_ROW_DELIMITER,
                date_format="%d/%m/%Y")
if len(DST_COL_DELIMITER) > 1:
    logging.info("Replacing temporary delimiter")
    with fileinput.FileInput(DST_FILE, inplace=True, backup='.bak') as f:
        for line in f:
            print(line.replace(delimiter, DST_COL_DELIMITER), end="")
logging.info("CONVERSION finished")
