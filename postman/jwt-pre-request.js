/**
 * JWT Pre-Request Script for Postman
 * ===================================
 * 
 * This script automatically handles JWT authentication before each request.
 * It checks if a valid token exists, refreshes it if expired, and attaches
 * it to the request header.
 * 
 * Required Environment Variables:
 *   - auth_url: The identity service URL (e.g., https://auth.company.com)
 *   - client_id: Your service's client ID
 *   - client_secret: Your service's client secret
 * 
 * Variables Set by This Script:
 *   - jwt_token: The current valid JWT token
 *   - jwt_expiry: Token expiration timestamp (Unix seconds)
 * 
 * Usage:
 *   1. Add this script to your collection's "Pre-request Script" tab
 *   2. Set the required environment variables
 *   3. All requests in the collection will automatically be authenticated
 */

// Configuration: Buffer time before expiry to refresh (60 seconds)
const EXPIRY_BUFFER_SECONDS = 60;

// Get current timestamp in seconds
const now = Math.floor(Date.now() / 1000);

// Retrieve stored token and expiry from environment
const storedToken = pm.environment.get("jwt_token");
const storedExpiry = pm.environment.get("jwt_expiry");

// Check if we have a valid, non-expired token
const tokenIsValid = storedToken && storedExpiry && (now < storedExpiry - EXPIRY_BUFFER_SECONDS);

if (tokenIsValid) {
    // Token is still valid, no action needed
    console.log("✓ Using existing JWT token (expires in " + (storedExpiry - now) + " seconds)");
} else {
    // Token is missing or expired, need to refresh
    console.log("⟳ JWT token missing or expired, requesting new token...");
    
    // Get auth configuration from environment
    const authUrl = pm.environment.get("auth_url");
    const clientId = pm.environment.get("client_id");
    const clientSecret = pm.environment.get("client_secret");
    
    // Validate required variables are present
    if (!authUrl || !clientId || !clientSecret) {
        console.error("✗ Missing required environment variables:");
        if (!authUrl) console.error("  - auth_url is not set");
        if (!clientId) console.error("  - client_id is not set");
        if (!clientSecret) console.error("  - client_secret is not set");
        throw new Error("Cannot authenticate: missing environment variables");
    }
    
    // Build the token request
    const tokenRequest = {
        url: authUrl + "/oauth/token",
        method: "POST",
        header: {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        },
        body: {
            mode: "urlencoded",
            urlencoded: [
                { key: "grant_type", value: "client_credentials" },
                { key: "client_id", value: clientId },
                { key: "client_secret", value: clientSecret },
                { key: "scope", value: "refunds:read refunds:write" }
            ]
        }
    };
    
    // Send the token request synchronously
    pm.sendRequest(tokenRequest, function (err, response) {
        if (err) {
            console.error("✗ Token request failed:", err);
            throw new Error("Authentication failed: " + err);
        }
        
        // Check for successful response
        if (response.code !== 200) {
            console.error("✗ Token request returned status " + response.code);
            console.error("  Response:", response.text());
            throw new Error("Authentication failed with status " + response.code);
        }
        
        // Parse the response
        const jsonResponse = response.json();
        
        if (!jsonResponse.access_token) {
            console.error("✗ No access_token in response:", jsonResponse);
            throw new Error("Authentication response missing access_token");
        }
        
        // Calculate expiry time
        // Default to 1 hour (3600 seconds) if expires_in not provided
        const expiresIn = jsonResponse.expires_in || 3600;
        const expiryTimestamp = now + expiresIn;
        
        // Store the token and expiry in environment
        pm.environment.set("jwt_token", jsonResponse.access_token);
        pm.environment.set("jwt_expiry", expiryTimestamp);
        
        console.log("✓ New JWT token obtained (expires in " + expiresIn + " seconds)");
    });
}
