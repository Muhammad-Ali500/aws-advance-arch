import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
} from "amazon-cognito-identity-js";
import { COGNITO_CONFIG, API_BASE_URL } from "./config.js";

const userPool = new CognitoUserPool(COGNITO_CONFIG);
let currentUser = null;

function show(elId, data) {
  document.getElementById(elId).textContent =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

document.getElementById("si-btn").onclick = () => {
  const username = document.getElementById("si-username").value;
  const password = document.getElementById("si-password").value;
  const cognitoUser = new CognitoUser({ Username: username, Pool: userPool });
  const authDetails = new AuthenticationDetails({ Username: username, Password: password });

  cognitoUser.authenticateUser(authDetails, {
    onSuccess: (session) => {
      currentUser = cognitoUser;
      show("si-result", { signedInAs: username });
    },
    onFailure: (err) => show("si-result", "Error: " + err.message),
  });
};

document.getElementById("so-btn").onclick = () => {
  if (currentUser) currentUser.signOut();
  currentUser = null;
  show("si-result", "Signed out.");
};

function getAccessToken() {
  return new Promise((resolve, reject) => {
    const user = userPool.getCurrentUser();
    if (!user) return reject(new Error("Not signed in"));
    user.getSession((err, session) => {
      if (err) return reject(err);
      resolve(session.getAccessToken().getJwtToken());
    });
  });
}

document.getElementById("stats-btn").onclick = async () => {
  try {
    const token = await getAccessToken();
    const resp = await fetch(`${API_BASE_URL}/admin/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const body = await resp.json();
    show("api-result", resp.status === 200 ? body : { status: resp.status, ...body });
  } catch (err) {
    show("api-result", "Error: " + err.message);
  }
};
