import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { isId, newId, sslConfig } from "../src/config/db.js";

describe("database config", () => {
    it("picks TLS by host unless DATABASE_SSL says otherwise", () => {
        const supabase = "postgresql://postgres.ref:pw@aws-0-eu-central-1.pooler.supabase.com:6543/postgres";
        assert.equal(sslConfig("postgres://postgres:pw@localhost:5432/db", ""), false);
        assert.equal(sslConfig("postgres://postgres:pw@127.0.0.1/db", ""), false);
        assert.deepEqual(sslConfig(supabase, ""), { rejectUnauthorized: false });
        assert.equal(sslConfig(supabase, "disable"), false);
        assert.deepEqual(sslConfig(supabase, "verify", "CERT"), { ca: "CERT", rejectUnauthorized: true });
        assert.throws(() => sslConfig(supabase, "verify", ""), /DATABASE_CA_CERT/);
    });

    it("generates 24-hex ids the ai-service accepts", () => {
        const ids = new Set(Array.from({ length: 1000 }, newId));
        assert.equal(ids.size, 1000);
        assert.ok([...ids].every(isId));
        assert.equal(isId("x".repeat(24)), false);
        assert.equal(isId(undefined), false);
    });
});
