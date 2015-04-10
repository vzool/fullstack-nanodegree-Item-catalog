# Full Stack Nanodegree Item Catalog


This is a python web application working with a Database as a Back-End.
Which is provide a Front-End interface make users make there own catalog with items inside it too.

All person will allowed to browse all catalog and items, and he/she can make their own Catalog and share them among Catalog Item App community.

## File Structure

I organized the project with considerations based on trustful functionality.

```
	templates			(application html files)
	app.py				(application start file)
	database_setup.py	(Database Setup)
```
## Database Structure

```SQL

-- Authentication table

CREATE TABLE person (
	id INTEGER NOT NULL, 
	name VARCHAR(250) NOT NULL, 
	email VARCHAR(250) NOT NULL, 
	password VARCHAR(250) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id)
)


-- Catalog table

CREATE TABLE catalog (
	id INTEGER NOT NULL, 
	name VARCHAR(250) NOT NULL, 
	person_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(person_id) REFERENCES person (id)
)

-- Item Catalog table

CREATE TABLE catalog_item (
	id INTEGER NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	description VARCHAR(250), 
	catalog_id INTEGER, 
	person_id INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(catalog_id) REFERENCES catalog (id), 
	FOREIGN KEY(person_id) REFERENCES person (id)
)

```

## Instructions

To Test this application you will need to following those steps:

### Server side

First you need to initialize Database:

```
$ python database_setup.py
``` 

And Finally, start server by:

```
$ python app.py
```

Then application server will run on port 5000.


### Server side(Vagrant option)
To avoid wrong configuration you can test this system as a Virtual Machine(VM), and I will tell you how in Debian Linux like:

First, install those packages:
```
$ sudo apt-get install virtualbox vagrant
```
Finally fire up vm
```
$ vagrant up --provider virtualbox
```
It will take some time to download ubuntu

### Client side

Open your browser with this URL:

```
http://127.0.0.1:5000
```

## Requirements

### Server side

You will need a Python 2.x language installed in your server system with some libraries:

- python-sqlalchemy
- python-flask
- python-requests
- Flask-Login
- oauth2client
- requests

### Client side

To run this Web Application you will need a browser which should be in specific versions that fully supports the JavaScript language, which those browsers and versions are:

- Chrome: 4.0+
- IE(Internet Explorer): 9.0+
- Firefox: 2.0+
- Safari: 3.1+
- Opera: 9.0+

## Licence

It's Completely Free. But, Do whatever you like to do on your own full responsibility;

This licence is known with [MIT License](http://vzool.mit-license.org/) in professional networks.