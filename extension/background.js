importScripts("shared.js", "background-core.js");
const broker = new XSD.Broker(chrome);
const ready = broker.init();
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  ready.then(() => broker.dispatch(message, sender)).then(
    data => respond({ok: true, data}),
    error => respond({ok: false, error: {
      code: error instanceof XSD.ClientError ? error.code : "operation_failed",
      retryable: error instanceof XSD.ClientError && error.retryable
    }})
  );
  return true;
});
