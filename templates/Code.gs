/**
 * 🚀 SUBSTACK RFK: GOOGLE APPS SCRIPT WEB APP
 * 
 * ⚠️ SETUP INSTRUCTIONS:
 * 1. Go to Project Settings (Gear Icon ⚙️) on the left.
 * 2. Under "Script Properties", click "Add script property".
 * 3. Property: WEB_APP_SECRET | Value: (Your random secure password).
 * 4. Click "Save script properties".
 * 5. Click "Deploy" -> "New Deployment".
 * 6. Click the "gear" ⚙️ next to "Select type" and choose "Web app".
 * 7. Set "Execute as" to: "Me (<your email>)".
 * 8. Set "Who has access" to: "Anyone" (Don't worry, your WEB_APP_SECRET protects it).
 * 9. Click "Deploy" -> "Authorize Access" (if prompted).
 * 10. Copy the "Web app URL" (it ends in /exec) and add it to your GitHub Variables.
 * 
 * 🔄 RE-DEPLOYMENT WARNING:
 * Every time you edit this code, you MUST click "Deploy" -> "New Deployment" 
 * for the changes to take effect. If you don't, the Web App URL will 
 * continue to run your OLD code. Always update the URL in GitHub if it changes!
 * 
 * ℹ️ This script manages the Triage Sheet (Rows 1: Instructions, 2: Headers, 3+: Data).
 */

var SECRET_PROP_NAME = "WEB_APP_SECRET";
var CURRENT_VERSION = "1.0";

/**
 * Authentication and Version Check middleware.
 */
function authenticate(request) {
  var props = PropertiesService.getScriptProperties();
  var secret = props.getProperty(SECRET_PROP_NAME);
  
  // 1. Secret Check
  if (!secret) {
    return { success: false, error: "Unauthorized: Secret not set", status: 401 };
  }

  var providedSecret = request.parameter.secret || (request.postData && JSON.parse(request.postData.contents).secret);
  var providedVersion = request.parameter.version || (request.postData && JSON.parse(request.postData.contents).version);

  if (providedSecret !== secret) {
    return { success: false, error: "Unauthorized: Secret mismatch", status: 401 };
  }

  // 2. Version Check
  if (providedVersion !== CURRENT_VERSION) {
    return { success: false, error: "VERSION_MISMATCH: App Script is v" + CURRENT_VERSION, status: 400 };
  }

  return { success: true };
}

/**
 * GET Handler: Used for fetching pending actions.
 */
function doGet(e) {
  var auth = authenticate(e);
  if (!auth.success) {
    return ContentService.createTextOutput(auth.error).setMimeType(ContentService.MimeType.TEXT);
  }

  var action = e.parameter.action;
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  
  if (action === "get_pending") {
    var data = sheet.getDataRange().getValues();
    // Headers are now on Row 2 (index 1)
    var headers = data[1];
    var results = [];
    
    // Data now starts on Row 3 (index 2)
    for (var i = 2; i < data.length; i++) {
      var row = data[i];
      var status = row[headers.indexOf("Status")];
      if (status && (status.toString().toUpperCase() === "APPROVED" || status.toString().toUpperCase() === "SKIP")) {
        var obj = {};
        headers.forEach(function(header, index) {
          obj[header] = row[index];
        });
        results.push(obj);
      }
    }
    return ContentService.createTextOutput(JSON.stringify(results)).setMimeType(ContentService.MimeType.JSON);
  }

  return ContentService.createTextOutput("Invalid Action").setMimeType(ContentService.MimeType.TEXT);
}

/**
 * POST Handler: Used for appending emails and updating status.
 */
function doPost(e) {
  var auth = authenticate(e);
  if (!auth.success) {
    return ContentService.createTextOutput(auth.error).setMimeType(ContentService.MimeType.TEXT);
  }

  var data = JSON.parse(e.postData.contents);
  var action = data.action;
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  // Headers are now on Row 2
  var headers = sheet.getRange(2, 1, 1, sheet.getLastColumn()).getValues()[0];

  if (action === "append") {
    var row = headers.map(function(h) {
      return data[h] || "";
    });
    // Insert new row at Row 3 (pushing existing Row 3 down)
    // This ensures it inherits data row styling rather than header styling
    sheet.insertRowBefore(3);
    sheet.getRange(3, 1, 1, row.length).setValues([row]);
    return ContentService.createTextOutput("Success").setMimeType(ContentService.MimeType.TEXT);
  }

  if (action === "update_status") {
    var msgId = data["Message-ID"];
    var newStatus = data["Status"];
    var msgIdCol = headers.indexOf("Message-ID") + 1;
    var statusCol = headers.indexOf("Status") + 1;
    
    // Data search starts from Row 3
    var numRows = sheet.getLastRow() - 2;
    if (numRows < 1) {
       return ContentService.createTextOutput("No data found").setMimeType(ContentService.MimeType.TEXT);
    }
    
    var values = sheet.getRange(3, msgIdCol, numRows, 1).getValues();
    for (var i = 0; i < values.length; i++) {
      if (values[i][0].toString() === msgId.toString()) {
        // Update the row (i is 0-indexed relative to Row 3)
        sheet.getRange(i + 3, statusCol).setValue(newStatus);
        return ContentService.createTextOutput("Success").setMimeType(ContentService.MimeType.TEXT);
      }
    }
    return ContentService.createTextOutput("Message-ID not found").setMimeType(ContentService.MimeType.TEXT);
  }

  return ContentService.createTextOutput("Invalid Action").setMimeType(ContentService.MimeType.TEXT);
}
