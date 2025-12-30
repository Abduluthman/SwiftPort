const country = "US"; // example; you could make this dynamic
fetch(`/api/esim/packages?country=${country}`, {
  headers: {
    "Authorization": `Bearer ${localStorage.getItem("token")}`
  }
})
.then(res => res.json())
.then(data => {
  const container = document.getElementById("packages");
  container.innerHTML = ""; // clear container first
  data.forEach(pkg => {
    container.innerHTML += `
      <div class="card">
        <p>${pkg.data}GB</p>
        <p>$${pkg.price}</p>
        <button onclick="buyEsim('${pkg.id}')">Buy</button>
      </div>
    `;
  });
});

function buyEsim(planId) {
  fetch("/api/esim/buy", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${localStorage.getItem("token")}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ plan_id: planId })
  })
  .then(res => res.json())
  .then(data => {
    if(data.success){
      alert("eSIM purchased successfully!");
      console.log("eSIM info:", data.esim);
    } else {
      alert(data.error);
    }
  })
  .catch(err => console.error(err));
}