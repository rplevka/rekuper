from config import settings
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restx import Api, Resource, fields, Namespace
from sqlalchemy.exc import IntegrityError

app = Flask('__name__')

pg_creds = f'{settings.postgres.username}:{settings.postgres.password}'
pg_host = settings.postgres.host
if len(pg_host.split('://')) == 1:
    app.logger.warning('DB connection schema not provided, assuming "postgres://"')
    pg_host = f'postgres://{pg_host}'

app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{pg_creds}@{settings.postgres.host}/{settings.postgres.db}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

api = Api(app, doc='/api/docs')  # Swagger UI will be available at /api/docs
ns = api.namespace('api', description='API operations')

sat_version_model = api.model('SatVersion', {
    'id': fields.Integer(readOnly=True, description='The unique identifier of a SatVersion'),
    'jenkins_job': fields.String(required=True, description='The Jenkins job'),
    'sat_version': fields.String(required=True, description='The Sat version')
})

instance_model = api.model('Instance', {
    'id': fields.Integer(readOnly=True, description='The unique identifier of an Instance'),
    'name': fields.String(required=True, description='The name of the instance'),
    'flavor': fields.String(required=True, description='The flavor of the instance'),
    'image': fields.String(required=True, description='The image of the instance'),
    'jenkins_url': fields.String(required=True, description='The Jenkins URL'),
    'job_sat_version': fields.String(required=True, description='The Sat version of the root automation job'),
    'sat_version_id': fields.Integer(required=True, description='The Sat version ID'),
    'first_seen': fields.Integer(description='First seen timestamp'),
    'last_seen': fields.Integer(description='Last seen timestamp')
})

container_model = api.model('Container', {
    'id': fields.Integer(readOnly=True, description='The unique identifier of a Container'),
    'name': fields.String(required=True, description='The name of the container'),
    'image': fields.String(required=True, description='The image of the container'),
    'job_sat_version': fields.String(required=True, description='The Sat version of the root automation job'),
    'first_seen': fields.Integer(description='First seen timestamp'),
    'last_seen': fields.Integer(description='Last seen timestamp')
})

class SatVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jenkins_job = db.Column(db.String(200), nullable=False)
    sat_version = db.Column(db.String(32, collation='numeric'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'jenkins_job': self.jenkins_job,
            'sat_version': self.sat_version,
        }

class Instance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    flavor = db.Column(db.String(200), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    sat_version_id = db.Column(db.Integer, db.ForeignKey('sat_version.id'), nullable=False)
    first_seen = db.Column(db.DateTime, nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'flavor': self.flavor,
            'image': self.image,
            'sat_version_id': self.sat_version_id,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }

@ns.route('/instances')
class InstanceList(Resource):
    @api.expect(instance_model)
    def post(self):
        data = request.json
        job_sat_version = data.get('job_sat_version')
        jenkins_url = data.get('jenkins_url')
        first_seen = data.get('first_seen')
        last_seen = data.get('last_seen')

        if jenkins_url is None:
            return {'message': 'jenkins_url is required'}, 400

        # Query SatVersion model
        sat_version_record = SatVersion.query.filter_by(jenkins_job=jenkins_url).first()

        if not sat_version_record:
            if job_sat_version is None:
                return {'message': 'job_sat_version is required'}, 400
            app.logger.info(f'jenkins build for {job_sat_version}, {jenkins_url} not found, creating new record')
            # Create new SatVersion if it does not exist
            sat_version_record = SatVersion(
                sat_version=job_sat_version,
                jenkins_job=jenkins_url
            )
            db.session.add(sat_version_record)
            db.session.commit()

        if first_seen:
            first_seen = datetime.fromtimestamp(first_seen)
        if last_seen:
            last_seen = datetime.fromtimestamp(last_seen)

        instance = Instance.query.filter_by(name=data['name']).first()
        if instance:
            app.logger.debug(f'matching instance: {instance}: last_seen={instance.last_seen} {last_seen}')
            # Update existing instance
            if first_seen and first_seen < instance.first_seen:
                app.logger.debug(f'updating first_seen from {instance.first_seen} to {first_seen}')
                instance.first_seen = first_seen
            if last_seen and last_seen > instance.last_seen:
                app.logger.debug(f'updating last_seen from {instance.last_seen} to {last_seen}')
                instance.last_seen = last_seen
            instance.flavor = data['flavor']
            instance.image = data['image']
            instance.sat_version_id = sat_version_record.id
            db.session.add(instance)
        else:
            # Create new instance
            instance = Instance(
                name=data['name'],
                flavor=data['flavor'],
                image=data['image'],
                sat_version_id=sat_version_record.id,
                first_seen=first_seen,
                last_seen=last_seen
            )
            db.session.add(instance)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Duplicate key value violates unique constraint'}, 409

        return instance.to_dict(), 201

class Container(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    image = db.Column(db.String(200), nullable=False)
    sat_version_id = db.Column(db.Integer, db.ForeignKey('sat_version.id'), nullable=False)
    first_seen = db.Column(db.DateTime, nullable=True)
    last_seen = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'image': self.image,
            'sat_version_id': self.sat_version_id,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
        }

@ns.route('/containers')
class ContainerList(Resource):
    @api.expect(container_model)
    def post(self):
        data = request.json
        sat_version = data.get('job_sat_version')
        jenkins_url = data.get('jenkins_url')
        first_seen = data.get('first_seen')
        last_seen = data.get('last_seen')

        # Query SatVersion model
        sat_version_record = SatVersion.query.filter_by(sat_version=sat_version, jenkins_job=jenkins_url).first()

        if not sat_version_record:
            app.logger.info(f'jenkins build for {sat_version}, {jenkins_url} not found, creating new record')
            # Create new SatVersion if it does not exist
            sat_version_record = SatVersion(
                sat_version=sat_version,
                jenkins_job=jenkins_url
            )
            db.session.add(sat_version_record)
            db.session.commit()

        if first_seen:
            first_seen = datetime.fromtimestamp(first_seen)
        if last_seen:
            last_seen = datetime.fromtimestamp(last_seen)

        container = Container.query.filter_by(name=data['name']).first()
        if container:
            app.logger.debug(f'matching container: {container}: last_seen={container.last_seen} {last_seen}')
            # Update existing container record 
            if first_seen and first_seen < container.first_seen:
                app.logger.debug(f'updating first_seen from {container.first_seen} to {first_seen}')
                container.first_seen = first_seen
            if last_seen and last_seen > container.last_seen:
                app.logger.debug(f'updating last_seen from {container.last_seen} to {last_seen}')
                container.last_seen = last_seen
            container.image = data['image']
            container.sat_version_id = sat_version_record.id
            db.session.add(container)
        else:
            container = Container(
                name=data['name'],
                image=data['image'],
                sat_version_id=sat_version_record.id,
                first_seen=first_seen,
                last_seen=last_seen
            )
        try:
            db.session.add(container)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {'message': 'Duplicate key value violates unique constraint'}, 409

        return container.to_dict(), 201

if __name__ == '__main__':
    app.run(debug=True)