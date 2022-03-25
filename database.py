# Copyright 2022 University of New South Wales, Ingham Institute

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect, timeit
import _mssql
import pymssql

from datastore import get_datastore

import logging
logger = logging.getLogger(__name__)

# SQL Query to retrieve records for patients in a clinical trial
# TODO Add center specific OIS SQL query in here, '%%%MRN%%%' is replaced with
# MRN list for query.
QUERY_CLINICAL_TRIALS = """"""

# SQL Query to retrieve records for patients who have finished treatment
# TODO Add center specific OIS SQL query in here, '%%%MRN%%%' is replaced with
# MRN list for query.
QUERY_PATIENT_FINISHED_TREATMENT = """"""

# SQL Query to retrieve records for patients who have 4D cone beam data
# TODO Add center specific OIS SQL query in here, '%%%MRN%%%' is replaced with
# MRN list for query.
QUERY_PATIENT_HAS_4D = """"""

# Perform the query on OIS to fetch clinical trials
def fetch_clinical_trials(mrns):

    if len(QUERY_CLINICAL_TRIALS) == 0:
        logger.error("OIS query missing, please add in database.py")
        return ""

    return query_ois(QUERY_CLINICAL_TRIALS.replace('%%%MRN%%%',mrns))

# Perform the query on OIS to fetch finished treatments
def fetch_patient_finished_treatment(mrns):

    if len(QUERY_PATIENT_FINISHED_TREATMENT) == 0:
        logger.error("OIS query missing, please add in database.py")
        return ""

    return query_ois(QUERY_PATIENT_FINISHED_TREATMENT.replace('%%%MRN%%%',mrns))

# Perform the query on OIS to fetch 4d cone beams
def fetch_patient_has_4d(mrns):

    if len(QUERY_PATIENT_HAS_4D) == 0:
        logger.error("OIS query missing, please add in database.py")
        return ""

    return query_ois(QUERY_PATIENT_HAS_4D.replace('%%%MRN%%%',mrns))

# Perform the query on OIS and return the results as a dict
def query_ois(query):

    logger.debug(str(query))
    datastore = get_datastore()

    if not "host" in datastore["ois_config"] or len(datastore['ois_config']['host']) == 0:
        logger.error("OIS connection configuration missing")

    if len(query) == 0:
        logger.error("OIS query missing, please add in database.py")

    conn = None
    result = None

    start_time = timeit.default_timer()

    # Run query on mssql and return a list of dicts of the results
    try:

        logger.info('Will query OIS')

        conn = pymssql.connect(server=datastore['ois_config']['host'],
            user=datastore['ois_config']['user'],
            password=datastore['ois_config']['pass'],
            database=datastore['ois_config']['db'])

        cursor = conn.cursor(as_dict=True)

        cursor.execute(query)

        result = cursor.fetchall()

    except:
        logger.exception('Exception with query')

    finally:
        if conn:
            conn.close()

    query_duration = timeit.default_timer() - start_time

    logger.info('Query completed in ' + str(query_duration))

    logger.debug(str(result))

    return result
