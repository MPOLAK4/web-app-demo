# Problem

Had my own problem (and probably many others), AI and it's spatial reasoning in figuring out which specific elements it wishes to put during UI / UX design is rather poor. From at least my own experience and from viewing others, Claude UI / UX is notoriously verbose in it's excessive usage of staccato's, duplicative information being displayed or unnecessary flavor.

Partially this can be solved by relying on ImageGen to generate buttons and such, writing quirks can be subjugated, but ultimately there still exists the seemingly persistent UX faults.


## Initial requirements

<!-- Give every requirement an ID so tests can cite it later:-->
R1. Headless / User interface for a wireframe, user can modify the wireframe as they wish. 
R2. Wireframe 'blocks' are converted into a spec sheet for either a coder AI or a ImageGen for creating a complete UI frontend.
R3. AI is given enough of a spec sheet to know how to create it's own proposed wireframe, either for user to inspect or itself.
R4. The application is capable of testing the states/flow of the program, seeing if there's any potential conflicts with the proposed UI / UX wireframe.
R5. Wireframe blocks contain a rough representation of what information it conveys; should be generic of an identifier that if an AI reads the state of the page, it should be able to determine that duplicative information or instructions is being displayed.
