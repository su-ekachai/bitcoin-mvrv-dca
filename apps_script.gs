// Bound script for the signals spreadsheet.
// Deploy: Extensions > Apps Script > paste > Deploy > New deployment >
// Web app, execute as Me, access "Anyone" > copy URL into SHEETS_WEBHOOK_URL.
function doPost(e) {
  const row = JSON.parse(e.postData.contents);
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName("signals") || ss.insertSheet("signals");
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(["date", "price", "mvrv", "sth_mvrv", "tier", "multiplier", "amount"]);
  }
  sheet.appendRow([row.date, row.price, row.mvrv, row.sth_mvrv, row.tier, row.multiplier, row.amount]);
  return ContentService.createTextOutput(JSON.stringify({ ok: true })).setMimeType(
    ContentService.MimeType.JSON
  );
}
