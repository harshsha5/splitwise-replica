# Prompts

## Feature 1 
```
Task: Build an expense split management app. Something like splitwise. 

Specifications:
1. Design the feature for adding and managing expenses.
2. Adding an expense includes: title, amount, paid by, participants, split type (equal), date, and optional category.
3. Have a tag based system to add participants and paid by. One should be able to add participants by typing the name and pressing enter. More names can then be added. Similarly there can be more than one person who paid for the expense. Assume equal pay split for now.
4. Also allow the user to edit and delete the expense after adding it.
5. Ensure after editing the expense that the total amount paid matches the total amount owed.
6. The participants in the participants list and paid by list can be removed by pressing the X on the tag to remove.
7. There has to be at least one person in the participant list and paid by list.
8. The payer should be added to the participants list by default. The payer can however be removed once editing the expense.
9. Assume the current user to be Veer.
10. Show the net amount the current user owes or is owed.
11. Can we build this in python?
12. You can install the required dependency after creating a virtual env for python
```

## Feature 2
```
Task: Let us try and support options for unequal amounts paid by the payers.

Specifications:
1. Add buttons under the paid by tab when adding people if the expenses are paid equally or unequally
2. Equally is easy to handle. In this case the total amount paid is equally paid by the payers.
3. If unequally is selected- we want to be able to manually add the amounts paid by the payers.
4. Validate that the total amount payed matches the sum of the individual amounts paid
5. Also update the edit expense option to support this. Where the user can switch from equally to unequally and vice versa.
6. If a user is removed from the paid by list- their name should now not appear if the unequal paid by split is shown. If only one user remains on deletion- the amount paid by that person should automatically change to the total amount.
```

## Feature 3 
```
Task: Let us try and support options for unequal amounts owed by participants

Specifications:
1. Add buttons below the participants list to indicate if the amount owed should be split equally or unequally.
2. Equally is easy- where in the total amount is split equally across all the people in the participant list.
3. In unequally, the user should be allowed to enter values of how much each person in the participant list owes.
4. Validate that the total amount paid is equal to the total amount owed.
5. This change should also be supported in the editing of the expense. 
6. The user should be allowed to update the expense to unequal or equal split.
7. If there is only one person in the participant list- they by default owe the entire amount.
8. The participant list cannot be empty.
```

## Feature 4
```
Task: Can we try to beautify the app.

Specifications:
1. Maintain the same functionality of the app. None of the functionality logic should change.
2. Change the UI of the app to be more sleek and modern. Make use of the right colors to make the app more appealing.
3. Make sure the colors are easy on the eyes- not too bright.
4. Make sure the buttons are clearly visible and don’t blend into the background due to the same color.
```