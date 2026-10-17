import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
} from "amazon-cognito-identity-js";
import { COGNITO_CONFIG, API_BASE_URL } from "./config.js";

const userPool = new CognitoUserPool(COGNITO_CONFIG);
let currentUser = null;

function show(elId, data) {
  document.getElementById(elId).textContent =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

document.getElementById("su-btn").onclick = () => {
  const username = document.getElementById("su-username").value;
  const email = document.getElementById("su-email").value;
  const password = document.getElementById("su-password").value;
  const attrs = [new CognitoUserAttribute({ Name: "email", Value: email })];

  userPool.signUp(username, password, attrs, null, (err, result) => {
    if (err) return show("su-result", "Error: " + err.message);
    show("su-result", "Signed up. Check email/local logs for the verification code, then confirm below.");
  });
};

document.getElementById("cf-btn").onclick = () => {
  const username = document.getElementById("cf-username").value;
  const code = document.getElementById("cf-code").value;
  const cognitoUser = new CognitoUser({ Username: username, Pool: userPool });

  cognitoUser.confirmRegistration(code, true, (err, result) => {
    if (err) return show("cf-result", "Error: " + err.message);
    show("cf-result", "Confirmed - you can sign in now.");
  });
};

document.getElementById("si-btn").onclick = () => {
  const username = document.getElementById("si-username").value;
  const password = document.getElementById("si-password").value;
  const cognitoUser = new CognitoUser({ Username: username, Pool: userPool });
  const authDetails = new AuthenticationDetails({ Username: username, Password: password });

  cognitoUser.authenticateUser(authDetails, {
    onSuccess: (session) => {
      currentUser = cognitoUser;
      show("si-result", {
        signedInAs: username,
        accessTokenExpiresIn: session.getAccessToken().getExpiration(),
      });
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

document.getElementById("public-btn").onclick = async () => {
  try {
    const resp = await fetch(`${API_BASE_URL}/public`);
    show("api-result", await resp.json());
  } catch (err) {
    show("api-result", "Error: " + err.message);
  }
};

document.getElementById("me-btn").onclick = async () => {
  try {
    const token = await getAccessToken();
    const resp = await fetch(`${API_BASE_URL}/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    show("api-result", await resp.json());
  } catch (err) {
    show("api-result", "Error: " + err.message);
  }
};
