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

import yaml

import logging
logger = logging.getLogger(__name__)

# Define path to YAML settings file
SETTINGS_FILE = 'settings.yaml'

# Read YAML from the datastore file, if it doesn't exist
# init with some empty values
def get_datastore():

    try:
        with open(SETTINGS_FILE, 'r') as f:
            datastore = yaml.load(f)
    except:
        datastore = {}

    if not 'xvi_paths' in datastore:
        datastore['xvi_paths'] = []

    if not 'ois_config' in datastore:
        datastore['ois_config'] = {}

    if not 'ignore_mrns' in datastore:
        datastore['ignore_mrns'] = []

    if not 'email_reports_config' in datastore:
        datastore['email_reports_config'] = {}

    return datastore

# Write YAML from the datastore file
def set_datastore(datastore):

    with open(SETTINGS_FILE, 'w') as f:
        yaml.dump(datastore, f)

    logger.debug('Saved Datastore to ' + SETTINGS_FILE + ' ' + str(datastore))
