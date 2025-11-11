<!--
Sync Impact Report

- Version change: none -> 1.0.0
- Modified principles: none
- Added sections: Article X: Governance
- Removed sections: none
- Templates reviewed:
	- .specify/templates/plan-template.md ✅ reviewed (Constitution Check present)
	- .specify/templates/spec-template.md ✅ reviewed
	- .specify/templates/tasks-template.md ✅ reviewed (contains sample tasks that must be replaced by generator)
	- .specify/templates/commands/ ⚠ missing - no command templates found; please verify commands folder
	- specs/001-screenshot-organizer/ ✅ reviewed

- Follow-up TODOs:


-->

# Project Constitution

Constitution Version: 1.0.0

Ratification Date: 2025-11-11

Last Amended: 2025-11-11

## Article I: Core Principles
1. **Local-First Processing**: Always prioritize local processing methods (OCR, local models) over external API calls
2. **Privacy by Design**: User data never leaves their machine except for GPT-4 orchestration (no images sent externally)
3. **Performance Transparency**: Always report which processing method was used and its performance metrics
4. **Cost Efficiency**: Minimize external API costs by maximizing local processing

## Article II: Technical Standards
1. **Python Best Practices**: Follow PEP 8, use type hints, document all functions
2. **Error Handling**: All operations must fail gracefully with clear error messages
3. **Modular Architecture**: Clean separation between MCP server, vision processing, and chat interface
4. **Protocol Compliance**: Strict adherence to MCP (Model Context Protocol) specifications

## Article III: Code Quality Requirements
1. **Test Coverage**: Minimum 80% test coverage for core functionality
2. **Documentation**: All modules, classes, and public functions must have docstrings
3. **Configuration**: All configurable parameters must be externalized to environment variables or config files
4. **Logging**: Comprehensive logging at appropriate levels (DEBUG, INFO, WARNING, ERROR)

## Article IV: User Experience
1. **Response Time**: Text-heavy screenshots must process in <50ms via OCR
2. **Batch Processing**: Support efficient batch processing with progress indicators
3. **Clear Feedback**: Always inform users about processing method, time, and results
4. **Intuitive Interface**: Terminal interface should be simple and conversational

## Article V: Development Workflow
1. **Incremental Development**: Build and test each component independently
2. **Test-Driven Development**: Write tests before implementation where applicable
3. **Version Control**: Commit frequently with clear, descriptive messages
4. **Dependency Management**: Use requirements.txt with pinned versions

## Article VI: Security & Privacy
1. **No External Image Transmission**: Images are never sent to external services
2. **Local Model Priority**: Use local models (Tesseract, Phi-3 Vision) exclusively for image processing
3. **Secure Configuration**: API keys stored in environment variables, never hardcoded
4. **Data Retention**: Process and organize files without creating unnecessary copies

## Article VII: Performance Optimization
1. **Tiered Processing**: OCR first (fast), then local vision model (slower) only when needed
2. **Efficient Categorization**: Use keyword-based classification for OCR results
3. **Batch Optimization**: Process multiple files efficiently with parallel processing where safe
4. **Resource Management**: Properly manage memory and file handles

## Article VIII: Extensibility
1. **Plugin Architecture**: Design to allow easy addition of new categorization rules
2. **Configurable Categories**: Allow users to customize categories and classification rules
3. **Model Flexibility**: Support swapping vision models without major refactoring
4. **MCP Tool Extensibility**: Easy addition of new MCP tools

## Article IX: Maintenance
1. **Clear Logging**: Comprehensive logging for debugging and monitoring
2. **Error Recovery**: Graceful degradation when components fail
3. **Update Path**: Clear documentation for updating dependencies and models
4. **Backward Compatibility**: Maintain compatibility with existing organized file structures

## Article X: Governance

1. **Amendment Procedure**: Amendments to this constitution MUST be proposed in a pull request that links to the reasoned change and any affected specs/templates. Amendments are accepted when at least two maintainers approve the PR. Emergency fixes (security/privacy) MAY be merged with a single maintainer approval but MUST be followed by a post-merge review.

2. **Versioning Policy**: This document follows semantic versioning for governance changes:
	- MAJOR version: Breaking governance changes (principle removal or re-definition that is backward-incompatible)
	- MINOR version: Addition of a principle or material expansion of guidance
	- PATCH version: Clarifications, wording, typo fixes, or non-semantic refinements
	When in doubt, propose a minor bump and include reasoning in the PR description.

3. **Compliance Review**: Before Phase 0 research or a production release, a Constitution Check MUST be run (see `.specify/templates/plan-template.md`) and any deviations MUST be documented with an acceptance justification in the spec's review section.

4. **Publication & Record**: Every amendment MUST update the `Last Amended` date in this file and include a one-sentence summary of the change at the top of the file within the Sync Impact Report comment block.

5. **Governance Contacts**: Maintain a `MAINTAINERS.md` or use the repository CODEOWNERS to list approvers responsible for constitution amendments and compliance reviews.

6. **Audit Trail**: Organizations implementing this repository SHOULD maintain an audit log of amendments (PRs and approvals) and periodically (quarterly) review the constitution for relevance.