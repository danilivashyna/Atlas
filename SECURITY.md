# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of Atlas seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please Do Not

- **Do not** open a public GitHub issue for security vulnerabilities
- **Do not** discuss the vulnerability publicly until it has been addressed

### Please Do

1. **Email us** at [INSERT SECURITY EMAIL] with:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Possible impact of the vulnerability
   - Any suggested fixes (if available)

2. **Use encryption** if the vulnerability is sensitive:
   - [INSERT PGP KEY IF APPLICABLE]

3. **Be patient** - We will acknowledge your email within 48 hours and send a more detailed response within 5 business days

### What to Expect

1. **Acknowledgment**: We'll confirm receipt of your vulnerability report within 48 hours

2. **Investigation**: We'll investigate the issue and determine its severity and impact

3. **Updates**: We'll keep you informed about our progress via email

4. **Resolution**: Once the vulnerability is fixed:
   - We'll notify you before the public announcement
   - We'll credit you in the security advisory (unless you prefer to remain anonymous)
   - We'll publish a security advisory on GitHub

### Severity Classification

We classify vulnerabilities using the following categories:

#### Critical
- Remote code execution
- Authentication bypass
- Privilege escalation
- Data exfiltration

#### High
- Denial of service
- Information disclosure (sensitive data)
- Cross-site scripting (XSS) in web interfaces

#### Medium
- Information disclosure (non-sensitive)
- Security misconfiguration with limited impact

#### Low
- Issues with minimal security impact
- Theoretical vulnerabilities

## Security Best Practices for Users

### Data Privacy

Atlas handles semantic embeddings and text data. Follow these practices:

1. **Sensitive Data**: Do not input sensitive personal information or credentials
2. **Ephemeral Mode**: Use ephemeral mode when processing sensitive content
3. **Logging**: Review logging configuration to ensure sensitive data is not logged

### Model Security

1. **Checkpoints**: Verify checksums (SHA-256) of downloaded model checkpoints
2. **Updates**: Keep Atlas updated to the latest version
3. **Dependencies**: Regularly update dependencies to patch vulnerabilities

### API Security

If deploying the FastAPI server:

1. **Authentication**: Implement authentication for production deployments
2. **Rate Limiting**: Enable rate limiting to prevent abuse
3. **HTTPS**: Always use HTTPS in production
4. **Input Validation**: All inputs are validated, but monitor for unexpected patterns
5. **CORS**: Configure CORS appropriately for your use case

### Configuration

1. **Secrets**: Never commit API keys, tokens, or credentials to version control
2. **Environment Variables**: Use environment variables for sensitive configuration
3. **File Permissions**: Ensure model files and configuration have appropriate permissions

## Known Security Considerations

### Data Handling

- **User Input**: All text input is processed through the encoder/decoder
- **Vectors**: Semantic vectors are numeric arrays with no executable code
- **Logging**: By default, we do not log raw user input (see security features)

### Security Features

1. **No Raw Text Logging**: User input text is not logged by default
2. **Ephemeral Mode**: Option to process data without persistence
3. **Input Sanitization**: All inputs are validated and sanitized
4. **Error Messages**: Error messages do not expose system internals

### Potential Risks

1. **Adversarial Inputs**: Like all ML systems, Atlas may be vulnerable to adversarial examples
2. **Model Bias**: The model may inherit biases from training data
3. **Resource Exhaustion**: Very long inputs could cause resource issues (we have limits)

## Security Updates

We will publish security advisories for:
- Critical and high-severity vulnerabilities
- Issues that affect a significant number of users
- Vulnerabilities that have been publicly disclosed

Security updates will be released as patch versions (e.g., 0.1.1, 0.1.2).

## Security Hall of Fame

We appreciate security researchers who help us keep Atlas secure:

<!-- List of security researchers who have responsibly disclosed vulnerabilities -->
- *Be the first to help us improve security!*

## Questions

If you have questions about this security policy, please open a discussion on GitHub or contact us at [INSERT CONTACT EMAIL].

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

---

Last updated: 2025-01-19
