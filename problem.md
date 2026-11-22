# Problem

Had my own problem (and probably many others), AI and it's spatial reasoning in figuring out which specific elements it wishes to put during UI / UX design is rather poor. From at least my own experience and from viewing others, Claude UI / UX is notoriously verbose in it's excessive usage of staccato's, duplicative information being displayed or unnecessary flavor.

Partially this can be solved by relying on ImageGen to generate buttons and such, writing quirks can be subjugated, but ultimately there still exists the seemingly persistent UX faults.


## Round 1 requirements

<!-- Give every requirement an ID so tests can cite it later:-->
R1. Headless / User interface for a wireframe, user can modify the wireframe as they wish. 
R2. Wireframe 'blocks' are converted into a spec sheet for either a coder AI or a ImageGen for creating a complete UI frontend.
R3. AI is given enough of a spec sheet to know how to create it's own proposed wireframe, either for user to inspect or itself.
R4. The application is capable of testing the states/flow of the program, seeing if there's any potential conflicts with the proposed UI / UX wireframe.
R5. Wireframe blocks contain a rough representation of what information it conveys; should be generic of an identifier that if an AI reads the state of the page, it should be able to determine that duplicative information or instructions is being displayed.

## Round 2 requirements

R6. Ensure that coder/Image Gen specs outputted by the wireframe model is detailed; expecting every block to have a spec sheets worth of style and design for consistency
R7. Blocks can be marked to carry the same style/design choice
R8. Broadly expand the level of UI options available
R9. Implement a mode where the user can navigate the wireframe as if it was an actual UI.

## Round 3 requirements

R10. Add the ability to output a html/png/other file formats of the UI, allow for any state of the UI to be shown in. This is so an AI/user can show how the mockup would look for a certain UI / UX setup.
R11. Data standins; when reading something like "file.value", have the ability to replace it with placeholder text when displayed. This is the equivalent of being in 'live' mode rather than 'debug' mode.

## Round 4 requirements

R12. Try to not have the application open up a server, AI should be able to handle closing the server down when it's done using it. Server should have a 5 minute timeout where it shuts itself down if nothing pinged it
R13. Create a html file you can click to open within a browser, application will be able to work.


## Round 5 requirements

R14. Implement some example UI layouts for the user/AI to see an example of the expected I/O.
R15. Review the spec sheet for UI creation; AI should consider or ask for how many iterations should be done on the same UI piece, changing it every time if needed. 


