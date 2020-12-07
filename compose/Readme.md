# KnowledgeHub CKAN  

## Running KnowledgeHub using docker-compose
To start KnowledgeHub using docker-compose, from this directory simply run
```sh
docker-compose build
docker-compose up
```
Check if KnowledgeHub was successfully started on http://localhost:5000. 

### Configuration
In order to configure KnowledgeHub within docker-compose we use both build/up time variables loaded via the [.env](./.env) file, and runtime variables loaded via the [.ckan-env](./.ckan-env) file. 

Variables in the [.env](./.env) file are loaded when running `docker-compose build` and `docker-compose up`, while variables in [.ckan-env](./.ckan-env) file are used withing the CKAN container at runtime to configure CKAN and CKAN extensions using [ckanext-envvars](https://github.com/okfn/ckanext-envvars).