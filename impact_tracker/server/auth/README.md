# Auth adapters



## Active: per-user cookie session



File: [`sessionAuth.js`](./sessionAuth.js)



- User pastes a Mantis API token from **My Account → API Tokens**

- Bridge validates via `GET /api/rest/users/me`

- Token + user are stored in an **httpOnly cookie session** (not a process-wide singleton)

- Optional **Authorization** header passthrough for scripts — does not mutate the session

- Routes: `POST /api/auth/login` (alias `POST /api/auth/token`), `POST /api/auth/logout`, `GET /api/auth/me`



## TokenAuthAdapter (interface reference)



File: [`tokenAdapter.js`](./tokenAdapter.js)



Thin class documenting the AuthAdapter shape (`login` / `logout` / `getUser` / …).  

The Express Bridge no longer uses a process-wide token singleton.



## PubKitAuthAdapter (future)



File: [`pubkitAdapter.stub.js`](./pubkitAdapter.stub.js)



Not implemented until the team confirms how [https://pubkit.newgen.co/](https://pubkit.newgen.co/) hands off to Mantis (cookie, redirect, shared session).



When ready:



1. Implement `PubKitAuthAdapter` with the same interface

2. Select via `AUTH_MODE=pubkit` in `server/index.js`

3. Replace the UI login page only — ticket list/detail/create stay the same

