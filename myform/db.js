const mysql = require('mysql2');  // or 'mysql' if using mysql package

const db = mysql.createConnection({
  host: 'localhost',
  user: 'root',  // replace with your username
  password: 'root',  // replace with your password
  database: 'login_system'  // replace with your database name
});

db.connect((err) => {
  if (err) {
    console.error('Error connecting to the database:', err.stack);
    return;
  }
  console.log('Connected to the database as id ' + db.threadId);
});

module.exports = db;
