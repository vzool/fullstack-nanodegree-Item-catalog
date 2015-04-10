import requests, os
import random, string
import httplib2, json

from werkzeug.routing import BaseConverter

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

from flask import make_response
from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash, send_from_directory

app = Flask(__name__)

client_secret_file = 'client_secret_404731601094-8lv7aqee2gdp3vun964is8p9p0csgasn.apps.googleusercontent.com.json'
CLIENT_ID = json.loads(
	open(client_secret_file, 'r').read()
)['web']['client_id']

######################## [DATABASE] ########################
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Person, Catalog, CatalogItem

engine = create_engine('sqlite:///catalog_item.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
db = DBSession()
######################## [DATABASE] ########################

# Token function
def token():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
	session['state'] = state
	return state

# Home
@app.route('/')
@app.route('/index')
@app.route('/home')
# no 404 page handle, just redirect user to home page
@app.errorhandler(404)
def index(error = None):
	last_catalog = None
	catalog = None
	if 'person_id' in session:
		last_catalog = db.query(Catalog).join(Catalog.person).filter(Catalog.person_id != session['person_id']).order_by(desc(Catalog.created_at)).limit(10)
		catalog = db.query(Catalog).join(Catalog.person).filter(Catalog.person_id == session['person_id']).order_by(desc(Catalog.created_at))
	else:
		last_catalog = db.query(Catalog).join(Catalog.person).order_by(desc(Catalog.created_at)).limit(10)
	return render_template('index.html', catalog = catalog, last_catalog = last_catalog, state = token())

@app.route('/login', methods=['GET','POST'])
def showLogin():

	# if user already sign in redirect to home
	if 'person_id' in session:
		return redirect('/')
	state = token()
	# generate random state to protect system from anti-forgery state token
	return render_template("login.html", STATE = state)

@app.route('/gconnect', methods=['POST'])
def gconnect():
	# Check validate state token
	if request.args.get('state') != session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	#Obtain authorization code
	code = request.data
  
	try:
		# Upgrade the authorization code into a credentials object
		oauth_flow = flow_from_clientsecrets(client_secret_file, scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check that the access token is valid.
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])
	# If there was an error in the access token info, abort.
	if result.get('error') is not None:
		response = make_response(json.dumps(result.get('error')), 500)
		response.headers['Content-Type'] = 'application/json'

	# Verify that the access token is used for the intended user.
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
		response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
		response = make_response(json.dumps("Token's client ID does not match app's."), 401)
		print "Token's client ID does not match app's."
		response.headers['Content-Type'] = 'application/json'
		return response

	stored_credentials = session.get('credentials')
	stored_gplus_id = session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
		response = make_response(json.dumps('Current user is already connected.'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Store the access token in the session for later use.
	session['credentials'] = credentials
	session['person_id'] = gplus_id
 
  
	#Get user info
	userinfo_url =  "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': credentials.access_token, 'alt':'json'}
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	# save data user in session
	session['person_name'] = data['name']
	session['person_picture'] = data['picture']
	session['person_email'] = data['email']

	# cache user in person database for reference
	is_person_exists = db.query(Person).filter_by(
		email = session['person_email']
	)

	if not is_person_exists.count():
		person = Person(
			name = session['person_name'],
			email = session['person_email'],
			google_id = session['person_id']
		)
		db.add(person)
		db.commit()

		session['person_id'] = person.id
	else:
		session['person_id'] = is_person_exists.one().id

	response = make_response(json.dumps('Welcome'), 200)
	response.headers['Content-Type'] = 'application/json'
	return response

# Logout
#DISCONNECT - Revoke a current user's token and reset their session
@app.route('/logout', methods=['POST'])
def logoutAction():
	# Only disconnect a connected user.
	credentials = session.get('credentials')
	if credentials is None:
		response = make_response(json.dumps('Current user not connected.'),401)
		response.headers['Content-Type'] = 'application/json'
		return response 
  
	access_token = credentials.access_token
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]

	# remove session data about person
	session.pop('person_id', None)
	session.pop('person_name', None)
	session.pop('person_email', None)
	session.pop('picture', None)
	session.pop('gplus_id', None)
	session.pop('credentials', None)
	session.pop('state', None)

	return redirect(url_for('index'))

# Create catalog by /catalog/create via POST and GET requests
# Update catalog by /catalog/catalog_id via POST and GET requests
# parameters:
#	- catalog_id: serial number for a catalog
#
#	note: all parameters are None by default
@app.route('/catalog/<int:id>/edit', methods=['POST', 'GET'])
@app.route('/catalog/create', methods=['POST', 'GET'])
def createCatalogAction(id = None):

	# if person is not logged in, redirect to home
	# if 'person_id' not in session:
	# 	return redirect(url_for('index'))

	if request.method == 'POST':
		
		# check if it is create
		if id != None:

			# Cross-Site Request Forgery (CSRF) protection
			if request.form['token'] != session['state']:
				catalog = db.query(Catalog).filter_by(id = id)
				flash("Error in Token, try again")
				if catalog.count():
					return render_template('catalog_form.html', state = token(), catalog = catalog.one())
				else:
					return render_template('catalog_form.html', state = token(), catalog = catalog)

			# select old catalog for update
			catalog = db.query(Catalog).filter_by(id = id).one()
			catalog.name = request.form['name']
			db.add(catalog)
			db.commit()
			
			# notify person and redirect to home
			flash("Your Catalog has been updated!")
			return redirect(url_for('index'))

		else:

			# Cross-Site Request Forgery (CSRF) protection
			if request.form['token'] != session['state']:
				flash("Error in Token, try again")
				return render_template('catalog_form.html', state = token())

			# query to check if catalog is exists in person account
			is_catalog_exists = db.query(Catalog).filter_by(
				name = request.form['name'],
				person_id = session['person_id']
			)

			# if not exists, create new catalog
			if not is_catalog_exists.count():

				catalog = Catalog(
					name = request.form['name'],
					person_id = session['person_id']
				)

				db.add(catalog)
				db.commit()
				
				# notify person with created
				flash("Catalog has been created!")
				return redirect(url_for('index'))

			# notify person with duplicated catalog
			flash("Catalog already exists in your!")
			return render_template('catalog_form.html', state = token())
	else:

		if id == None:
			# create new catalog form
			return render_template('catalog_form.html', state = token())
		else:
			# update catalog form
			catalog = db.query(Catalog).filter_by(id = id)
			if catalog.count():
				return render_template('catalog_form.html', catalog = catalog.one(), state = token())

			return redirect(url_for('index'))

	return render_template('catalog_form.html', state = token())

# Drop Catalog
@app.route('/catalog/<int:id>/drop', methods=['GET'])
def dropCatalogAction(id = None):
	
	# Cross-Site Request Forgery (CSRF) protection
	if request.args.get('token') != session['state']:
		flash("Error in Token, try again")
		return redirect(url_for('index'))	

	if id != None:
		# delete all items from catalog
		db.query(CatalogItem).filter(CatalogItem.catalog_id == id).delete()
		# delete catalog itself
		db.query(Catalog).filter(Catalog.id == id).delete()

	flash("Your Catalog and its items has been deleted!")
	return redirect(url_for('index'))

####################################### [ ITEMS ] #######################################


# Create catalog items by /catalog/catalog_id/item/create via POST and GET requests
# Update catalog items by /catalog/catalog_id/item/item_id/edit via POST and GET requests
# parameters:
#	- catalog_id: serial number for a catalog
#	- item_id: serial number for an item
#
#	note: all parameters are None by default
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/edit', methods=['POST', 'GET'])
@app.route('/catalog/<int:catalog_id>/item/create', methods=['POST', 'GET'])
def createItemAction(catalog_id = None, item_id = None):
	
	# if person is not logged in, redirect to home
	if 'person_id' not in session:
		return redirect('/catalog/%s/items' % catalog_id)

	catalog = db.query(Catalog).filter_by(
		id = catalog_id
	)

	if catalog.count():
		
		catalog = catalog.one()

		if request.method == 'POST':
			
			if item_id != None:

				# Cross-Site Request Forgery (CSRF) protection
				if request.form['token'] != session['state']:
					flash("Error in Token, try again")
					item = db.query(CatalogItem).filter_by(id = item_id)
					if item.count():
						item = item.one()
						return render_template('item_form.html', catalog = catalog, item = item, state = token())
					else:
						return render_template('item_form.html', catalog = catalog, state = token())
				
				item = db.query(CatalogItem).filter_by(
					id = item_id,
					catalog_id = catalog_id
				)

				item = item.one()
				item.name = request.form['name']
				item.description = request.form['description']

				db.add(item)
				db.commit()

				flash("Your item has been updated.")

				return redirect('/catalog/%s/items' % catalog_id)

			else:

				# Cross-Site Request Forgery (CSRF) protection
				if request.form['token'] != session['state']:
					flash("Error in Token, try again")
					return render_template('item_form.html', catalog = catalog, state = token())

				# check if item exists inside this catalog
				name = request.form['name']
				description = request.form['description']

				is_item_exists = db.query(CatalogItem).filter_by(
					catalog_id = catalog_id,
					name = name
				)

				if not is_item_exists.count():
					item = CatalogItem(
						catalog_id = catalog_id,
						name = name,
						description = description
					)

					db.add(item)
					db.commit();
					flash("item has been added.")
					return redirect('/catalog/%s/items' % catalog_id)

				else:
					flash("This item is already exists this Catalog!")	
		else:
			
			if item_id != None:
				
				item = db.query(CatalogItem).filter_by(id = item_id)

				if item.count():
					item = item.one()
					return render_template('item_form.html', catalog = catalog, item = item, state = token())

			else:

				return render_template('item_form.html', catalog = catalog, state = token())

	return redirect(url_for('index'))

# Show Items for specific catalog
@app.route('/catalog/<int:catalog_id>/items', methods=['POST', 'GET'])
def catalogListItems(catalog_id):

	catalog = db.query(Catalog).filter(Catalog.id == catalog_id)

	if catalog.count():
		
		catalog = catalog.one()

		items = db.query(CatalogItem).filter(CatalogItem.catalog_id == catalog_id)

		return render_template("catalog_index.html", catalog = catalog, items = items, state = token())

	return redirect(url_for('index'))

# Drop item from Catalog
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/drop', methods=['POST', 'GET'])
def itemDropAction(catalog_id, item_id):

	# Cross-Site Request Forgery (CSRF) protection
	if request.args.get('token') != session['state']:
		flash("Error in Token, try again")
		return redirect('/catalog/%s/items' % catalog_id)

	# Check if person logged in
	if 'person_id' not in session:
		return redirect('/catalog/%s/items' % catalog_id)

	catalog = db.query(Catalog).filter(Catalog.id == catalog_id)

	if catalog.count():
		
		item = db.query(CatalogItem).filter_by(
			id = item_id,
			catalog_id = catalog_id
		)

		item.delete();

		flash("Your Item has been deleted from this Catalog.")
		return redirect('/catalog/%s/items' % catalog_id)

	return redirect(url_for('index'))

# Show one item
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>')
def catalogItem(catalog_id, item_id):
	item = db.query(CatalogItem).filter_by(id = item_id, catalog_id = catalog_id).one()
	return render_template("item_index.html", item = item, catalog_id = catalog_id)

####################################### [ JSON APIs ] #######################################
# list all json API URLs
@app.route('/JSON/info')
def infoJSON():
	return jsonify(api_info = {
		'/JSON/info' : "Services API Information",
		'/JSON' : "Current Community Catalog",
		'/catalog/JSON' : "Current Community Catalog",
		'/catalog/catalog_id/items/JSON' : "Current items in Community Catalog(parameter: catalog_id)",
		'/catalog/catalog_id/item/item_id/JSON' : "Select item in some Catalog(parameters: catalog_id, item_id)"
	})

# list all catalog in system
@app.route('/JSON')
@app.route('/catalog/JSON')
def catalogJSON():
	catalog = db.query(Catalog).all()
	return jsonify(catalog= [r.serialize for r in catalog])

# list all items for catalog in system
@app.route('/catalog/<int:catalog_id>/items/JSON')
def catalogMenuJSON(catalog_id):
	catalog = db.query(Catalog).filter_by(id = catalog_id).one()
	items = db.query(CatalogItem).filter_by(catalog_id = catalog_id).all()
	return jsonify(CatalogItem=[i.serialize for i in items])

# show item data in some catalog in system
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/JSON')
def catalogItemJSON(catalog_id, item_id):
	items = db.query(CatalogItem).filter_by(id = item_id).one()
	return jsonify(CatalogItem = items.serialize)

####################################### [ Startup point ] #######################################
if __name__ == '__main__':
	# Session encryption key
	app.secret_key = b'\xc2q;\x15z\t\xafT&\xfd\x81\x93\xfc^\xb9\xa0\xf4\xa6\x93\xc2\xe9\xd8\x94\x1d'
	app.debug = True
	app.run(host = '0.0.0.0', port = 5000)
