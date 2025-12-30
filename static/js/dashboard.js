const API_BASE = "http://127.0.0.1:5000/api";

fetch(`${API_BASE}/wallet`, {
  headers: {
    "Authorization": `Bearer ${localStorage.getItem("token")}`
  }
})
.then(res => res.json())
.then(data => {
  document.getElementById("balance").innerText = `$${data.balance}`;
});

const token = localStorage.getItem("token")
if(!token) window.location.href="/login"

// Wallet balance
fetch("/api/wallet", {
  headers: { Authorization: "Bearer " + token }
})
.then(res => res.json())
.then(data => {
  document.getElementById("balance").innerText = data.balance
})

// Transactions
fetch("/api/transactions", {
  headers: { Authorization: "Bearer " + token }
})
.then(res => res.json())
.then(data => {
  const container = document.getElementById("transactions")
  container.innerHTML = ""
  data.forEach(tx => {
    container.innerHTML += `
      <div class="card">
        <p>Reference: ${tx.reference}</p>
        <p>Type: ${tx.type}</p>
        <p>Amount: ${tx.amount}</p>
        <p>Status: ${tx.status}</p>
      </div>
    `
  })
})
