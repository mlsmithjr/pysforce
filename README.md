# pysforce

Library to authenticate with and make API calls to Salesforce.
This is a new library that's starting out very simple with the hope that
the python/salesforce community will swarm around it to create the 
definitive API toolkit.

*Feel free to fork, enhance, and submit pull requests.*


### Features:
* Supports single record operations fetch and update.
* Support large query results using a generator. 
* Plug-in authentication model.
* Currently supports user/pass and JWT authentication.

### Requirements

* Python 3.6+

### Installation

```
pip3 install pysforce
```

## Quick Start

##### simple password-based authentication
```python
from pysforce import OAuthPassword, SFClient

# authenticate to a sandbox (default)
myauth = OAuthPassword('myuser@mydomain.com.dev', 'mypassword')
client = SFClient(myauth)



```
##### JWT authentication
```python
from pysforce import OAuthPassword, SFClient

pubkey = None
with open('mykey.pem', 'r') as keyfile:
  pubkey = keyfile.read()
# authenticate to a sandbox (default)
myauth = OAuthJWT('myuser@mydomain.com.dev', consumer_key, pubkey)
client = SFClient(myauth)

```

##### execute a query
```python
for record in client.query('select id,name from account, owner.name'):
    id = record['id']
    name = record['name']
    ownername = record['owner']['name']
    print(f'{id}:{name}:{ownername}')
```

##### fetch and update a record by ID
```python
try:
  record = client.fetch_record('account', recordid, ['onboarding_status'])
  if record['onboarding_status'] != 'Complete':
    client.update_record('account', recordid, {'onboarding_status': 'Complete'})
except Exception as ex:
  print('record missing')

```

##### list tables available to my profile
```python
for sobject in client.get_sobject_list():
  print(sobject['name'])

```

##### list table details (metadata attributes)
```python
sobject = client.get_sobject_definition('account')
for k,v in sobject.items():
  print(f'{k} : {v}')

```

##### list table fields
```python
fieldlist = client.get_field_list('account')
for field in fieldlist:
  name = field['name']
  type = field['type']
  size = field['size']
  print(f'name={field}, type={type}, size={size}')

# or, you could get the field definition as a map keyed by name
fieldmap = client.get_field_map('account')
for key, val in fieldmap.items():
  type = val['type']
  size = val['size']
  print(f'name={key}, type={type}, size={size}')
```

##### record count
```python
reccount = client.record_count('account')
print(f'{reccount} records in account table')
```
