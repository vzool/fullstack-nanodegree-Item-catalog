import hashlib # to hash person password
from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash
app = Flask(__name__)

######################## [DATABASE] ########################
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Person, Catalog, CatalogItem

engine = create_engine('sqlite:///catalog_item.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
db = DBSession()
######################## [DATABASE] ########################

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
	return render_template('index.html', catalog = catalog, last_catalog = last_catalog)

# Sign up
@app.route('/signup', methods=['GET','POST'])
def signupAction():

	# if user already logged in redirect to home
	if 'person_name' in session:
		return redirect(url_for('index'))

	# if method is post
	if request.method == 'POST':

		is_email_exists = db.query(Person).filter_by(email = request.form['email'])

		if not is_email_exists.count():
			person = Person(
				name = request.form['name'],
				email = request.form['email'],
				# Hash person password with SHA-224-HEX
				password = hashlib.sha224(request.form['password']).hexdigest()
			)

			db.add(person)
			db.commit()
			
			# Auto login
			session['person_id'] = person.id
			session['person_name'] = person.name
			session['person_email'] = person.email

			# redirect to home
			return redirect(url_for('index'))
		else:
			flash("This email already taken by somebody!")
			return render_template('register.html')
	else:
		return render_template('register.html')

# Login
@app.route('/login', methods=['POST', 'GET'])
def loginAction():
	if request.method == 'POST':
		# Query Login if person has a validation
		valid_person = db.query(Person).filter_by(
			email = request.form['email'],
			password = hashlib.sha224(request.form['password']).hexdigest()
		)

		# if person valid, login him/her
		if(valid_person.count() == 1):
			
			# create session data about person
			session['person_id'] = valid_person.one().id
			session['person_name'] = valid_person.one().name
			session['person_email'] = valid_person.one().email
			
	return redirect(url_for('index'))

# Logout
@app.route('/logout', methods=['POST', 'GET'])
def logoutAction():
	# remove session data about person
	session.pop('person_id', None)
	session.pop('person_name', None)
	session.pop('person_email', None)
	return redirect(url_for('index'))

# Create/Update catalog
@app.route('/catalog/<int:id>/edit', methods=['POST', 'GET'])
@app.route('/catalog/create', methods=['POST', 'GET'])
def createCatalogAction(id = None):
	
	if request.method == 'POST':
		
		# check if it is create
		if id != None:

			# select old catalog for update
			catalog = db.query(Catalog).filter_by(id = id).one()
			catalog.name = request.form['name']
			db.add(catalog)
			db.commit()
			
			# notify person and redirect to home
			flash("Your Catalog has been updated!")
			return redirect(url_for('index'))

		else:

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
			return render_template('catalog_form.html')
	else:

		if id == None:
			# create new catalog form
			return render_template('catalog_form.html')
		else:
			# update catalog form
			catalog = db.query(Catalog).filter_by(id = id)
			if catalog.count():
				return render_template('catalog_form.html', catalog = catalog.one())

			return redirect(url_for('index'))

	return render_template('catalog_form.html')

# Drop Catalog
@app.route('/catalog/<int:id>/drop', methods=['GET'])
def dropCatalogAction(id = None):
	
	if id != None:
		# delete all items from catalog
		db.query(CatalogItem).filter(CatalogItem.catalog_id == id).delete()
		# delete catalog itself
		db.query(Catalog).filter(Catalog.id == id).delete()

	flash("Your Catalog and its items has been deleted!")
	return redirect(url_for('index'))

####################################### [ ITEMS ] #######################################

# Create/Update Catalog Items
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
					return render_template('item_form.html', catalog = catalog, item = item)

			else:

				return render_template('item_form.html', catalog = catalog)

	return redirect(url_for('index'))

# Show Items for specific catalog
@app.route('/catalog/<int:catalog_id>/items', methods=['POST', 'GET'])
def catalogListItems(catalog_id):

	catalog = db.query(Catalog).filter(Catalog.id == catalog_id)

	if catalog.count():
		
		catalog = catalog.one()

		items = db.query(CatalogItem).filter(CatalogItem.catalog_id == catalog_id)

		return render_template("catalog_index.html", catalog = catalog, items = items)

	return redirect(url_for('index'))

# Drop item from Catalog
@app.route('/catalog/<int:catalog_id>/item/<int:item_id>/drop', methods=['POST', 'GET'])
def itemDropAction(catalog_id, item_id):

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
