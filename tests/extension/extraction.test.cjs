const test = require("node:test");
const assert = require("node:assert/strict");
const {dom, tweet} = require("./helpers.cjs");
test("own text preserves whitespace, line breaks, Unicode, emoji image alt and links", () => {
  const c = dom(tweet('  Hello <span>世界</span><br><a href="/hashtag/test">#test</a> <img alt="😀">  '));
  const article = c.document.querySelector("article"), result = c.XSD.dom.extract(article);
  assert.equal(result.text, "  Hello 世界\n#test 😀  ");
  assert.equal(result.anchor.className, "controls");
});
test("block-formatted text retains line boundaries and nested header wrappers preserve placement", () => {
  const c = dom(tweet("<div>first</div><div>second</div>"));
  const article = c.document.querySelector("article");
  assert.equal(c.XSD.dom.extract(article).text, "first\nsecond");
  article.querySelector(".controls").innerHTML = '<div><button aria-label="Ask Grok">G</button></div><div><button data-testid="caret">…</button></div>';
  assert.equal(c.XSD.dom.extract(article).anchor.className, "controls");
});
test("quoted and nested posts are not concatenated or separately badged inside a parent", () => {
  const quote = `<div role="link"><div data-testid="tweetText">Quoted secret</div></div>
    <div data-testid="quoteTweet">${tweet("Nested quoted secret")}</div>`;
  const c = dom(tweet("Own public text", quote));
  const articles = c.document.querySelectorAll("article");
  assert.equal(c.XSD.dom.extract(articles[0]).text, "Own public text");
  assert.equal(c.XSD.dom.extract(articles[1]), null);
});
test("media-only, empty, ambiguous text and missing header anchors fail closed", () => {
  for (const markup of [
    tweet(""), tweet("  <br> "),
    tweet("one", '<div data-testid="tweetText">another unscoped text</div>'),
    '<article data-testid="tweet"><div data-testid="tweetText">text</div></article>',
    '<article data-testid="tweet"><div role="link"><div data-testid="tweetText">quote only</div></div><button data-testid="caret">…</button></article>'
  ]) {
    const c = dom(markup);
    assert.equal(c.XSD.dom.extract(c.document.querySelector("article")), null);
  }
});
test("exact text/anchor matching rejects edited and recycled nodes", () => {
  const c = dom(tweet("old text")), article = c.document.querySelector("article");
  const record = c.XSD.dom.extract(article);
  assert.equal(c.XSD.dom.stillMatches(article, record), true);
  article.querySelector('[data-testid="tweetText"]').textContent = "new text";
  assert.equal(c.XSD.dom.stillMatches(article, record), false);
  article.querySelector('[data-testid="tweetText"]').textContent = "old text";
  article.querySelector(".controls").replaceWith(article.querySelector(".controls").cloneNode(true));
  assert.equal(c.XSD.dom.stillMatches(article, record), false);
});
