const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");

const policy = require("../../bhf_web/static/narrative-presentation-policy.js");
const audit = JSON.parse(fs.readFileSync("docs/evidence-depth/ed7/source-verification-results.json", "utf8"));

test("reader policy keeps the 99 source-audit decisions separate from CKL governance", () => {
  const expected = new Map(audit.records.map((record) => [record.stable_ckl_id, record.presentation.tier]));
  assert.equal(policy.auditedRecordCount, 99);
  assert.deepEqual(policy.auditedTiers(), expected);
  const inaccessible = audit.records.find((record) => record.pass_a.outcome === "source_inaccessible_or_insufficiently_verified");
  assert.equal(policy.tierFor({id: inaccessible.stable_ckl_id, content_status: "published", human_review_required: false}), "withheld_from_reader_promotion");
  const qualified = audit.records.find((record) => record.presentation.tier === "available_on_demand");
  assert.equal(policy.tierFor({id: qualified.stable_ckl_id, content_status: "draft", human_review_required: true}), "available_on_demand");
});

test("unassessed CKL records require substantive passage-specific content as well as source details", () => {
  assert.equal(policy.tierFor({
    id: "ckl:example#claim:one",
    domain: "ckl",
    record_kind: "evidence",
    claim_text: "The passage describes a field purchase during the siege as a sign of future restoration.",
    applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "direct"}],
    sources: [{details_available: true, bibliographic_details: {title: "A source", author: "An author", locator: "p. 12"}}],
  }), "available_on_demand");
  assert.equal(policy.tierFor({
    id: "ckl:jeremiah",
    domain: "ckl",
    record_kind: "object",
    title: "Jeremiah",
    applicable_passage_anchors: [{reference: "Jeremiah 32:1-44", relationship: "primary"}],
    sources: [{details_available: true, bibliographic_details: {title: "A source", author: "An author", locator: "p. 12"}}],
  }), "withheld_from_reader_promotion");
  assert.equal(policy.tierFor({
    id: "ckl:example#claim:title-only",
    domain: "ckl",
    record_kind: "evidence",
    title: "A title",
    applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "direct"}],
    sources: [{details_available: true, bibliographic_details: {title: "A source", author: "An author", locator: "p. 12"}}],
  }), "withheld_from_reader_promotion");
  assert.equal(policy.tierFor({
    id: "ckl:example#claim:two",
    domain: "ckl",
    applicable_passage_anchors: [{reference: "Genesis 1:1", relationship: "direct"}],
    sources: [{details_available: false}],
  }), "withheld_from_reader_promotion");
  assert.equal(policy.tierFor({
    id: "ckl:example#claim:three",
    domain: "ckl",
    applicable_passage_anchors: [],
    sources: [{details_available: true, bibliographic_details: {title: "A source", author: "An author", locator: "p. 12"}}],
  }), "withheld_from_reader_promotion");
});

test("featured discovery wording separates textual observations from disputed explanations", () => {
  const details = policy.featuredDiscoveryForId("ckl:nahum#evidence:nahum-3-8-9-one-city-text-critical-proposal");
  assert.match(details.notice, /Masoretic/i);
  assert.match(details.notice, /Greek and Qumran/i);
  assert.match(details.uncertainty, /proposed historical explanation/i);
  assert.match(details.uncertainty, /manuscript image/i);
});

test("reader source notes describe citation access without treating checks as scholarly approval", () => {
  const nahum = {
    id: "ckl:nahum#evidence:nahum-3-8-9-one-city-text-critical-proposal",
  };
  const unsupported = {
    id: "ckl:sample#claim:not-audited",
  };
  const insufficient = audit.records.find((record) => record.presentation.tier === "withheld_from_reader_promotion");

  assert.match(policy.sourceNoteFor(nahum), /cited work.*listed below/i);
  assert.match(policy.sourceLimitFor(nahum), /Masoretic, Greek, and Qumran readings/i);
  assert.match(policy.sourceLimitFor(nahum), /not compared with an image of 4Q385a or another manuscript/i);
  assert.match(policy.sourceNoteFor(unsupported), /source is cited, but its support.*not independently checked/i);
  assert.match(policy.sourceNoteFor({id: insufficient.stable_ckl_id}), /could not be checked well enough to confirm/i);
  assert.doesNotMatch(policy.sourceNoteFor(nahum), /automated check|human scholarly review/i);
});
