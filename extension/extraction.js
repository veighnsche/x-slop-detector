/* Conservative X DOM adapter. Fail closed on ambiguous text or missing controls. */
(() => {
  "use strict";
  const X = globalThis.XSD;
  const TWEET = 'article[data-testid="tweet"]';
  function quoted(node, article) {
    for (let p = node.parentElement; p && p !== article; p = p.parentElement) {
      if (p.matches('article, [role="link"], [data-testid="quoteTweet"], [data-testid="card.wrapper"]')) return true;
    }
    return false;
  }
  function textOf(node) {
    if (node.nodeType === 3) return node.nodeValue;
    if (node.nodeType !== 1 || node.getAttribute("aria-hidden") === "true" ||
        node.hasAttribute("hidden") || node.matches("script, style")) return "";
    if (node.tagName === "BR") return "\n";
    if (node.tagName === "IMG") return node.getAttribute("alt") || "";
    let result = "", previousBlock = false;
    for (const child of node.childNodes) {
      const value = textOf(child);
      if (!value) continue;
      const block = child.nodeType === 1 && child.matches("div, p");
      if (result && (block || previousBlock) && !result.endsWith("\n") && !value.startsWith("\n")) result += "\n";
      result += value; previousBlock = block;
    }
    return result;
  }
  function extract(article) {
    if (!article.matches(TWEET) || article.parentElement?.closest(TWEET)) return null;
    const own = Array.from(article.querySelectorAll('[data-testid="tweetText"]'))
      .filter(n => n.closest(TWEET) === article && !quoted(n, article));
    const carets = Array.from(article.querySelectorAll('[data-testid="caret"]'))
      .filter(n => n.closest(TWEET) === article && !quoted(n, article));
    if (own.length !== 1 || carets.length !== 1) return null;
    const caret = carets[0].closest('button, [role="button"]');
    if (!caret || !article.contains(caret)) return null;
    // Insert before the entire Grok/menu group when both share a controls wrapper.
    let anchor = caret;
    const grok = Array.from(article.querySelectorAll(
      '[data-testid="grok"], button[aria-label*="Grok"], [role="button"][aria-label*="Grok"]'))
      .filter(n => n.closest(TWEET) === article && !quoted(n, article));
    if (grok.length) {
      let group = caret.parentElement;
      while (group && group !== article && !group.contains(own[0]) &&
          !group.querySelector('[data-testid="User-Name"]') && !group.contains(grok[0])) group = group.parentElement;
      if (!group || group === article || group.contains(own[0]) ||
          group.querySelector('[data-testid="User-Name"]')) return null;
      anchor = group;
    }
    const text = textOf(own[0]);
    if (!text.trim()) return null;
    return {text, anchor};
  }
  // Both exact content and anchor identity are needed when React recycles a node.
  function stillMatches(article, record) {
    const current = extract(article);
    return !!current && current.text === record.text && current.anchor === record.anchor;
  }
  X.dom = {TWEET, textOf, extract, stillMatches};
})();
