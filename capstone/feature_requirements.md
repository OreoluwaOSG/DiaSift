# DiaSift Response Feedback and Quality Tracking

## Background

DiaSift is an existing web application.

The application already handles the core question answering workflow and uses ChromaDB as part of its existing RAG implementation.

There is currently no separate application database specifically for feedback or response tracking.

The purpose of this feature is to introduce a lightweight mechanism for collecting and persistently storing user feedback on individual DiaSift responses.

## Goal

Allow a user to indicate whether a DiaSift response was helpful or not helpful and ensure that the feedback can be traced to the exact response that received it.

## Functional Requirements

FR1
Every completed DiaSift response should provide the user with a visible feedback option.

FR2
The user should be able to select:

Helpful

or

Not Helpful.

FR3
When a user selects Not Helpful, the system should allow them to optionally select or provide a reason.

Possible reasons can include:

Did not answer my question

Difficult to understand

Information seemed incorrect

Sources were not helpful

Other

FR4
Every DiaSift interaction that can receive feedback must have a unique response identifier.

FR5
Feedback must be associated with the response that received it.

FR6
Feedback must be stored persistently rather than existing only in frontend state.

FR7
The implementation should allow stored feedback to be reviewed later.

FR8
The system should record an appropriate timestamp for submitted feedback.

FR9
The system should distinguish between positive and negative feedback.

FR10
The implementation should appropriately handle DiaSift responses where the system refuses or declines to answer.

FR11
Submitting feedback must not cause DiaSift to regenerate the original answer.

FR12
Feedback functionality must not interfere with DiaSift's existing RAG, retrieval, safety, scope or evidence behaviour.

FR13
The solution should avoid unnecessarily storing personally identifiable information.

FR14
The agent should determine and justify an appropriate persistence approach based on the existing architecture.

Do not assume that an additional database technology already exists in the project.

FR15
Changes should follow the existing architecture and coding conventions where practical.

## Validation Requirements

The completed feature should demonstrate that:

A response can be rated.

Positive feedback can be submitted.

Negative feedback can be submitted.

A negative reason can be recorded.

Feedback survives beyond temporary frontend state.

Feedback can be connected to the exact response that received it.

Existing DiaSift questions still work.

Existing safety behaviour continues to work.

Existing evidence/source functionality continues to work.

Invalid feedback requests are handled appropriately.

The application does not expose secrets or sensitive internal information.

## Out of Scope

A full administrative analytics dashboard.

User accounts specifically for feedback.

Authentication redesign.

Changing DiaSift's RAG model.

Changing the medical knowledge base.

Redesigning the entire DiaSift interface.

Advanced feedback analytics.

Production cloud database infrastructure.