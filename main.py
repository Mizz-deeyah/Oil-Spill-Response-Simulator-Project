from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///incidents.db'
app.config['SECRET_KEY'] = 'replace-this-with-something-random'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class Incident(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spill_size = db.Column(db.Integer)
    wind_speed = db.Column(db.Integer)
    wind_direction = db.Column(db.String(10))
    sea_condition = db.Column(db.String(20))
    distance_to_shore = db.Column(db.Integer)
    oil_type = db.Column(db.String(10))
    risk_level = db.Column(db.String(20))
    spread_radius = db.Column(db.Float)
    time_to_shore = db.Column(db.Float)
    marine_life_impact = db.Column(db.String(20))
    shoreline_risk = db.Column(db.Float)
    action_taken = db.Column(db.String(30))
    containment_success = db.Column(db.Integer)
    cost = db.Column(db.Integer)
    outcome = db.Column(db.String(20))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            return "Access denied - admin only"
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return "Invalid email or password"

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_officer', methods=['GET', 'POST'])
@login_required
@admin_required
def add_officer():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        new_officer = User(
            email=email,
            password=generate_password_hash(password),
            role='officer'
        )

        db.session.add(new_officer)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('add_officer.html')

@app.route('/')
@login_required
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    spill_size = int(request.form['spill_size'])
    wind_speed = int(request.form['wind_speed'])
    wind_direction = request.form['wind_direction']
    sea_condition = request.form['sea_condition']
    distance_to_shore = int(request.form['distance_to_shore'])
    oil_type = request.form['oil_type']

    # Risk level logic
    if spill_size > 5000 and wind_speed > 25:
        risk_level = "Extreme"
    elif spill_size > 2000 or sea_condition == "Rough":
        risk_level = "High"
    elif sea_condition == "Moderate":
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # Spread radius logic
    if oil_type == "Light":
        base_radius = 10
    elif oil_type == "Medium":
        base_radius = 7
    else:  # Heavy
        base_radius = 4

    spread_radius = base_radius + (spill_size / 1000) + (wind_speed / 10)

    # Time to shore logic
    time_to_shore = distance_to_shore / (spread_radius / 2 + wind_speed / 5)

    # Marine life impact logic
    if risk_level == "Extreme":
        marine_life_impact = "Severe"
    elif risk_level == "High":
        marine_life_impact = "Moderate"
    else:
        marine_life_impact = "Low"

    # Shoreline risk logic
    shoreline_risk = max(0, 100 - (time_to_shore * 10))

    return render_template('results.html',
                           spill_size=spill_size,
                           wind_speed=wind_speed,
                           wind_direction=wind_direction,
                           sea_condition=sea_condition,
                           distance_to_shore=distance_to_shore,
                           oil_type=oil_type,
                           risk_level=risk_level,
                           spread_radius=f"{spread_radius:.1f}",
                           time_to_shore=f"{time_to_shore:.1f}",
                           marine_life_impact=marine_life_impact,
                           shoreline_risk=f"{shoreline_risk:.0f}")

@app.route('/respond', methods=['POST'])
@login_required
def respond():
    action = request.form['action']

    if action == "Deploy Booms":
        containment_success = 82
        cost = 3500000
    elif action == "Use Dispersants":
        containment_success = 65
        cost = 2000000
    elif action == "Skimmers":
        containment_success = 55
        cost = 1500000
    else:  # Do Nothing
        containment_success = 10
        cost = 0

    outcome = "Successful" if containment_success >= 60 else "Failed"

    new_incident = Incident(
        spill_size=int(request.form['spill_size']),
        wind_speed=int(request.form['wind_speed']),
        wind_direction=request.form['wind_direction'],
        sea_condition=request.form['sea_condition'],
        distance_to_shore=int(request.form['distance_to_shore']),
        oil_type=request.form['oil_type'],
        risk_level=request.form['risk_level'],
        spread_radius=float(request.form['spread_radius']),
        time_to_shore=float(request.form['time_to_shore']),
        marine_life_impact=request.form['marine_life_impact'],
        shoreline_risk=float(request.form['shoreline_risk']),
        action_taken=action,
        containment_success=containment_success,
        cost=cost,
        outcome=outcome
    )

    db.session.add(new_incident)
    db.session.commit()

    return render_template('outcome.html',
                           action=action,
                           containment_success=containment_success,
                           cost=f"{cost:,}",
                           outcome=outcome)

@app.route('/history')
@login_required
def history():
    all_incidents = Incident.query.all()
    return render_template('history.html', incidents=all_incidents)
if __name__ == '__main__':
    app.run(debug=True)