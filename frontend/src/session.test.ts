import { afterEach, describe, expect, it } from "vitest";

import { getActingMember, reloadActingMember, setActingMember } from "./session";

afterEach(() => window.sessionStorage.clear());

describe("acting member storage", () => {
  it("survives a reload through sessionStorage", () => {
    setActingMember({ id: 2, name: "Sam Rivera", isManager: false });

    expect(reloadActingMember()).toEqual({ id: 2, name: "Sam Rivera", isManager: false });
  });

  it("ignores stored data that isn't a valid choice", () => {
    window.sessionStorage.setItem("roadhouse.actingMember", '{"id":"two"}');
    expect(reloadActingMember()).toBeNull();

    window.sessionStorage.setItem("roadhouse.actingMember", "not json");
    expect(reloadActingMember()).toBeNull();
  });

  it("forgets the choice when cleared", () => {
    setActingMember({ id: 1, name: "Jordan Avery", isManager: true });
    setActingMember(null);

    expect(getActingMember()).toBeNull();
    expect(reloadActingMember()).toBeNull();
  });
});
