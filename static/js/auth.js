const API_BASE = ""  // Use "" if running frontend via Flask templates

function register() {
  const email = document.getElementById("email").value
  const password = document.getElementById("password").value

  fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  })
  .then(res => res.json())
  .then(data => {
    if(data.error){
      alert(data.error)
      return
    }
    localStorage.setItem("token", data.token)
    window.location.href = "/dashboard"
  })
}

function login() {
  const email = document.getElementById("email").value
  const password = document.getElementById("password").value

  fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  })
  .then(res => {
    if(!res.ok) return res.json().then(err => { throw err })
    return res.json()
  })
  .then(data => {
    localStorage.setItem("token", data.token)
    window.location.href = "/dashboard"
  })
  .catch(err => alert(err.error))
}
