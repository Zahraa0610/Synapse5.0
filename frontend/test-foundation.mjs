import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { transform } from "esbuild";

const source = await readFile(new URL("./src/api.js", import.meta.url), "utf8");
const compiled = await transform(source, {format:"esm", define:{"import.meta.env.VITE_API_BASE_URL":'"http://test/api"'}});
const values = new Map();
globalThis.localStorage = {getItem:key=>values.get(key)||null, setItem:(key,value)=>values.set(key,value), removeItem:key=>values.delete(key)};
let expired = false;
globalThis.window = {dispatchEvent:event=>{ if(event.type === "maak-session-expired") expired=true; }};
const {api, canVisit, homeFor, getToken, setToken} = await import("data:text/javascript;base64," + Buffer.from(compiled.code).toString("base64"));
for (const [role, path] of [["caregiver","/home"],["volunteer","/volunteer"],["donor","/donor"],["doctor","/doctor"],["nurse","/doctor"],["psychologist","/doctor"],["shelter_coordinator","/shelter"],["ngo","/ngo"],["ministry","/ministry"]]) {
  const user = {role, verification_status:"approved"};
  assert.equal(homeFor(role),path);
  assert.equal(canVisit(user,path),true);
  assert.equal(canVisit(user,"/me"),true);
  assert.equal(canVisit(user,role === "ministry" ? "/doctor" : "/ministry"),false);
}
assert.equal(canVisit(null,"/home"),false);
assert.equal(canVisit({role:"doctor",verification_status:"pending"},"/doctor"),false);
assert.equal(canVisit({role:"volunteer"},"/volunteer-pretend"),false);
setToken("test-session");
globalThis.fetch = async (url, options) => {
  assert.equal(url,"http://test/api/auth/me");
  assert.equal(options.headers.Authorization,"Bearer test-session");
  return {ok:true,json:async()=>({user:{role:"caregiver"}})};
};
assert.equal((await api("/auth/me")).user.role,"caregiver");
globalThis.fetch = async()=>({ok:false,status:401,json:async()=>({error:"Sign in required"})});
await assert.rejects(api("/auth/me"),/Sign in required/);
assert.equal(getToken(),null);
assert.equal(expired,true);
console.log("Frontend role routing, API configuration, bearer authentication and expiration checks passed");
