import logging
import json
import operator
from typing import List, Dict, Generator, Optional

from fastcache import lru_cache

from pysforce.auth import SFAuthenticator
from pysforce import SF_API_VERSION as _API_VERSION


class SFError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class SFClient:
    client = None
    _auth = None

    def __init__(self, auth: SFAuthenticator):
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
    def sobject_schema(self, sobject_name) -> Dict:
        """Returns detailed attributes about an sobject

        Parameters
        ----------
        sobject_name:
           Name of the sobject/table to inspect.

        Returns
        -------
        A dictionary representing all sobject attributes. (see Salesforce metadata docs for more):
        """
        sobject_doc = self._http_get('sobjects/{}/describe'.format(sobject_name), {})
        return sobject_doc

    def sobjects(self) -> List[Dict]:
        """Returns a list of available sobjects and minimal attributes for each

        Returns
        -------
        A list of dictionaries representing sobject attributes. (see Salesforce metadata docs for more):
        """
        response = self._http_get('sobjects/', {})
        sobject_list = response['sobjects']
        return sobject_list

    @lru_cache(maxsize=10, typed=False)
    def sobject_field_list(self, sobject_name: str) -> [Dict]:
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
        response = self._http_get('sobjects/%s/describe/' % (sobject_name.lower(),), {})
        fieldlist = response['fields']
        fieldlist.sort(key=operator.itemgetter('name'))
        return fieldlist

    def sobject_field_map(self, sobject_name: str) -> Dict:
        thelist = self.sobject_field_list(sobject_name.lower())
        return dict((f['name'].lower(), f) for f in thelist)

    ##
    # Data methods
    ##
    def fetch_record(self, sobject_name: str, recid: str, field_list: List = None) -> Dict:
        """
        Fetch a single record by primary key.
        :param sobject_name: name of the sobject (table)
        :param recid: unique recordid for the row to be returned
        :param field_list: optional, list of fields to return. If omitted, all fields are returned.
        :return: found record, or None
        """
        if field_list is None:
            fmap = self.sobject_field_map(sobject_name)
            field_list = fmap.keys()
        fieldstring = ','.join(field_list)
        url = 'sobjects/{0}/{1}'.format(sobject_name, recid)
        result = self._http_get(url, {'fields': fieldstring})
        return result

    def insert_record(self, sobject_name, user_params) -> str:
        data = self._http_post(sobject_name, user_params)
        return data['id'] if data else None

    def update_record(self, sobject_name: str, recid: str, user_params):
        self._http_patch(sobject_name, recid, user_params)

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

    def query_one(self, soql: str) -> Optional[Dict]:
        """
        Execute a query and return a single record

        :param soql: SOQL statement
        :return: first record found, or None
        """
        for rec in self.query(soql):
            return rec
        return None

    def call(self, urn: str) -> str:
        """call a custom REST endpoint

        :param urn: custom part of the full service URL
        :return raw text body of response
        """

        if urn is None or len(urn) == 0:
            raise ValueError("urn parameter is not valid")
        if urn[0] == '/':
            urn = urn[1:]
        fullurl = f'{self.service_url}/{urn}'
        response = self.client.get(fullurl)
        return response.text

    @property
    def service_url(self):
        return self._auth.service_url

    ##
    # REST API wrappers
    ##
    def _http_post(self, sobject_name: str, payload):
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

    def _http_get(self, resource, url_params):
        full_url = f'{self._auth.service_url}/services/data/v{_API_VERSION}/{resource}'
        response = self.client.get(full_url, params=url_params)
        if response.status_code == 404:
            return None
        result_payload = response.text
        response.raise_for_status()
        data = json.loads(result_payload)
        return data

    def _http_patch(self, sobject_name, recid, url_data):
        if isinstance(url_data, Dict):
            url_data = json.dumps(url_data)
        response = self.client.patch(
            '%s/services/data/v%s/sobjects/%s/%s/' % (self._auth.service_url, _API_VERSION, sobject_name, recid),
            data=url_data)
        response.raise_for_status()

    ##
    # Helpers
    ##

    def record_count(self, sobject_name: str, where_filter: str = None):
        """Returns the number of records in a table, possibly filtered

        :param where_filter: optional WHERE clause criteria for filtering the count
        :param sobject_name: name of the sobject to count
        """
        soql = 'select count() from ' + sobject_name
        if where_filter:
            soql += ' where ' + where_filter
        fullurl = f'{self._auth.service_url}/services/data/v{_API_VERSION}/query/'
        response = self.client.get(fullurl, params={'q': soql})
        response.raise_for_status()
        result = response.json()
        return result['totalSize']
