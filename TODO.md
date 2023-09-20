### ask_question.py
- [x] Send questions to admins 
  - [ ] Carry responses back & forth  
- [x] <s>Copy user's question to finQuestionCollection and get its _id value. Assign 'state'='in progress' to it</s> There are 2 collections for questions: `wip` & `fin`. each user can only have one document in wip. 
  - [ ] expert needs to set a question status as done to move the document to `fin`
- [ ] Back button for pictures. should old IDs be deleted?  
- [ ] Delete message IDs of photos (when?)
- [ ] dockerfile and docker-compose.yml
- [ ] CI/CD