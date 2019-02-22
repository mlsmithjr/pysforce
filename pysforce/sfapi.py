import logging
import json
import operator
from typing import List, Dict, Generator
from pysforce.auth import Authenticator
from pysforce import SF_API_VERSION as _API_VERSION


class SFError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SFClient:
    client = None
    _auth = None
    service_url = None

    def __init__(self, auth: Authenticator):
        self.logger = logging.getLogger('sfclient')
        if not auth.is_authenticated():
            raise Exception('not authenticated')
        self._auth = auth
        self.client = self._auth.client

    def close(self):
        self._auth = None

    ##
    # Metadata methods
    ##
    def get_sobject_definition(self, sobject_name) -> Dict:
        """Returns detailed attributes about an sobject

        Parameters
        ----------
        sobject_name:
           Name of the sobject/table to inspect.

        Returns
        -------
        A dictionary representing all sobject attributes. (see Salesforce metadata docs for more):
        """
        sobject_doc = self.get_http('sobjects/{}/describe'.format(sobject_name), {})
        return sobject_doc

    def get_sobject_list(self) -> List[Dict]:
        """Returns a list of available sobjects and minimal attributes for each

        Returns
        -------
        A list of dictionaries representing sobject attributes. (see Salesforce metadata docs for more):
        """
        response = self.get_http('sobjects/', {})
        sobject_list = response['sobjects']
        return sobject_list

    def get_field_list(self, sobject_name: str) -> List[Dict]:
        """Returns the list of field definitions for a given sobject

        Parameters
        ----------
        sobject_name:
           Name of the sobject/table to inspect.

        Returns
        -------
        A list of dictionaries representing all field attributes.  Each dictionary contains the following
        fields (see Salesforce metadata docs for more):

        Ex:
          {
            "autoNumber": false,
            "byteLength": 18,
            "calculated": false,
            "calculatedFormula": null,
            "cascadeDelete": false,
            "caseSensitive": false,
            "controllerName": null,
            "createable": true,
            "custom": false,
            "defaultValue": null,
            "defaultValueFormula": null,
            "defaultedOnCreate": true,
            "dependentPicklist": false,
            "deprecatedAndHidden": false,
            "digits": 0,
            "displayLocationInDecimal": false,
            "encrypted": false,
            "externalId": false,
            "extraTypeInfo": null,
            "filterable": true,
            "filteredLookupInfo": null,
            "groupable": true,
            "highScaleNumber": false,
            "htmlFormatted": false,
            "idLookup": false,
            "inlineHelpText": null,
            "label": "Created By ID",
            "length": 18,
            "mask": null,
            "maskType": null,
            "name": "CreatedById",
            "nameField": false,
            "namePointing": false,
            "nillable": false,
            "permissionable": false,
            "picklistValues": [],
            "precision": 0,
            "queryByDistance": false,
            "referenceTargetField": null,
            "referenceTo": [
              "User"
            ],
            "relationshipName": "CreatedBy",
            "relationshipOrder": null,
            "restrictedDelete": false,
            "restrictedPicklist": false,
            "scale": 0,
            "soapType": "tns:ID",
            "sortable": true,
            "type": "reference",
            "unique": false,
            "updateable": false,
            "writeRequiresMasterRead": false
          }

        """
        response = self.get_http('sobjects/%s/describe/' % (sobject_name,), {})
        fieldlist = response['fields']
        fieldlist.sort(key=operator.itemgetter('name'))
        return fieldlist

    def get_field_map(self, sobject_name: str) -> Dict:
        thelist = self.get_field_list(sobject_name)
        return dict((f['name'].lower(), f) for f in thelist)

    ##
    # Data methods
    ##
    def fetch_record(self, sobject_name: str, recid: str, field_list: List):
        fieldstring = ','.join(field_list)
        url = 'sobjects/{0}/{1}'.format(sobject_name, recid)
        result = self.get_http(url, {'fields': fieldstring})
        return result

    def insert_record(self, sobject_name, user_params) -> str:
        if isinstance(user_params, Dict):
            user_params = json.dumps(user_params)
        data = self.http_post(sobject_name, json.dumps(user_params))
        return data['id'] if data else None

    def update_record(self, sobject_name: str, recid: str, user_params):
        if isinstance(user_params, Dict):
            user_params = json.dumps(user_params)
        self.http_patch(sobject_name, recid, user_params)

    def query(self, soql: str) -> Generator:
        fullurl = f'{self._auth.service_url}/services/data/v{_API_VERSION}/query/'
        response = self.client.get(fullurl, params={'q': soql})
        response.raise_for_status()
        txt = response.text
        if isinstance(txt, str):
            payload = txt
        else:
            payload = str(txt, 'utf-8')
        data = json.loads(payload)
        recs = data['records']
        for rec in recs:
            yield (rec)
        while 'nextRecordsUrl' in data:
            next_records_url = data['nextRecordsUrl']
            if next_records_url is not None:
                response = self.client.get('%s%s' % (self._auth.service_url, next_records_url))
                txt = response.text
                if isinstance(txt, str):
                    payload = txt
                else:
                    payload = str(txt, 'utf-8')
                data = json.loads(payload)
                recs = data['records']
                for rec in recs:
                    yield (rec)
            else:
                break

    ##
    # REST API wrappers
    ##
    def http_post(self, sobject_name: str, payload):
        if isinstance(payload, Dict):
            payload = json.dumps(payload)
        try:
            fullurl = f'{self._auth.service_url}/services/data/v{_API_VERSION}/sobjects/{sobject_name}/'
            self.logger.debug('post %s', fullurl)
            response = self.client.post(fullurl, data=payload)
            response.raise_for_status()
        except Exception as ex:
            self.logger.error(ex)
            raise ex
        if 'errorCode' in response.text:
            self.logger.error('response: %s', response.text)
        data = json.loads(response.text)
        return data

    def get_http(self, resource, url_params):
        full_url = f'{self._auth.service_url}/services/data/v{_API_VERSION}/{resource}'
        response = self.client.get(full_url, params=url_params)
        result_payload = response.text
        response.raise_for_status()
        data = json.loads(result_payload)
        return data

    def http_patch(self, sobject_name, recid, url_data):
        if isinstance(url_data, Dict):
            url_data = json.dumps(url_data)
        response = self.client.patch(
            '%s/services/data/v%s/sobjects/%s/%s/' % (self._auth.service_url, _API_VERSION, sobject_name, recid),
            data=url_data)
        response.raise_for_status()

    ##
    # Helpers
    ##

    def record_count(self, sobject_name, where_filter: str = None):
        """Returns the number of records in a table, possibly filtered

         Parameters
         ----------
         where_filter:
            If given, only count records matching the given SOQL Where clause
        """
        soql = 'select count() from ' + sobject_name
        if where_filter:
            soql += ' where ' + where_filter
        fullurl = f'{self._auth.service_url}/services/data/v{_API_VERSION}/query/'
        response = self.client.get(fullurl, params={'q': soql})
        response.raise_for_status()
        result = response.json()
        return result['totalSize']
