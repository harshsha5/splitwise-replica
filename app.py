from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
import uuid
from models import Expense, Participant, SplitType, PaymentType

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Needed for flash messages

expenses = []

CURRENT_USER = "Veer"

def get_user_net_balance(user_name):
    """Calculate the net balance for a specific user across all expenses"""
    net_balance = 0.0
    
    for expense in expenses:
        user_participant = None
        for participant in expense.participants:
            if participant.name == user_name:
                user_participant = participant
                break
        
        if user_participant:
            # User is a participant: Positive = user is owed money, Negative = user owes money
            expense_balance = user_participant.amount_paid - user_participant.amount_owed
            net_balance += expense_balance
        
        # Check if user made external payments (paid but wasn't a participant)
        if user_name in expense.external_payments:
            # User paid for others without being a participant - they are owed this amount
            net_balance += expense.external_payments[user_name]
    
    return net_balance

def get_user_relationships(user_name):
    """Calculate individual balances between the user and each other user"""
    relationships = {}
    
    # Get all unique users across all expenses
    all_users = set()
    for expense in expenses:
        for participant in expense.participants:
            all_users.add(participant.name)
        for payer in expense.external_payments.keys():
            all_users.add(payer)
    
    # Calculate net balance between user and each other user
    for other_user in all_users:
        if other_user == user_name:
            continue
            
        net_between_users = 0.0
        
        for expense in expenses:
            balance_summary = expense.get_balance_summary()
            user_balance = balance_summary.get(user_name, 0.0)
            other_balance = balance_summary.get(other_user, 0.0)
            
            # Simple approach: if both users are in this expense, calculate direct relationship
            if user_balance != 0 and other_balance != 0:
                # If user paid more than they owed and other user paid less than they owed
                # Then other user effectively owes user money from this expense
                if user_balance > 0 and other_balance < 0:
                    # User overpaid, other user underpaid
                    shared_amount = min(abs(user_balance), abs(other_balance))
                    net_between_users += shared_amount
                elif user_balance < 0 and other_balance > 0:
                    # User underpaid, other user overpaid  
                    shared_amount = min(abs(user_balance), abs(other_balance))
                    net_between_users -= shared_amount
        
        # Only include relationships with non-zero balances
        if abs(net_between_users) >= 0.01:
            relationships[other_user] = net_between_users
    
    return relationships

@app.route('/')
def index():
    user_balance = get_user_net_balance(CURRENT_USER)
    user_relationships = get_user_relationships(CURRENT_USER)
    return render_template('index.html', expenses=expenses, user_balance=user_balance, 
                         user_relationships=user_relationships, current_user=CURRENT_USER)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        try:
            title = request.form['title']
            amount = float(request.form['amount'])
            paid_by = request.form['paid_by']
            # Parse multiple payers from the tag system
            payer_names = [name.strip() for name in paid_by.split(',') if name.strip()]
            # Use the first payer as the primary payer for display purposes
            primary_payer = payer_names[0] if payer_names else paid_by
            participants_str = request.form['participants']
            split_type = SplitType(request.form['split_type'])
            payment_type = PaymentType(request.form['payment_type'])
            category = request.form.get('category', '')
            
            # Auto-include payers in participants if not already there
            participant_names = [name.strip() for name in participants_str.split(',') if name.strip()]
            for payer_name in payer_names:
                if payer_name not in participant_names:
                    participant_names.append(payer_name)
            
            # Validate that at least one participant exists
            if not participant_names:
                flash("Error: At least one participant must be specified. Someone needs to owe money for this expense.", 'error')
                return render_template('add_expense.html')
            
            participants = [Participant(name=name) for name in participant_names]
            
            expense = Expense(
                id=str(uuid.uuid4()),
                title=title,
                amount=amount,
                paid_by=paid_by,  # Store full comma-separated list
                participants=participants,
                split_type=split_type,
                payment_type=payment_type,
                date=datetime.now(),
                category=category if category else None
            )
            
            # Handle payments based on payment type
            payments = {}
            # Initialize all participants with 0 payment
            for participant in participants:
                payments[participant.name] = 0.0
            
            if payment_type == PaymentType.EQUAL:
                # Distribute payment equally among payers
                per_payer_amount = amount / len(payer_names) if payer_names else amount
                for payer_name in payer_names:
                    payments[payer_name] = per_payer_amount
            else:  # PaymentType.UNEQUAL
                # Get unequal payment amounts from form
                unequal_payments = {}
                for payer_name in payer_names:
                    payment_field = f'payment_amount_{payer_name}'
                    if payment_field in request.form:
                        unequal_payments[payer_name] = float(request.form[payment_field])
                    else:
                        unequal_payments[payer_name] = 0.0
                
                # Validate unequal payments total
                if not expense.validate_unequal_payments(unequal_payments):
                    total_payments = sum(unequal_payments.values())
                    flash(f"Error: Total payments (${total_payments:.2f}) don't match expense amount (${amount:.2f})", 'error')
                    return render_template('add_expense.html')
                
                # Set the unequal payment amounts
                for payer_name, payment_amount in unequal_payments.items():
                    payments[payer_name] = payment_amount
                
            expense.set_payments(payments)
            
            # Handle split amounts based on split type
            if split_type == SplitType.UNEQUAL:
                # Get unequal split amounts from form
                unequal_splits = {}
                for participant in participants:
                    split_field = f'split_amount_{participant.name}'
                    if split_field in request.form:
                        unequal_splits[participant.name] = float(request.form[split_field])
                    else:
                        unequal_splits[participant.name] = 0.0
                
                # Validate unequal splits total
                if not expense.validate_unequal_splits(unequal_splits):
                    total_splits = sum(unequal_splits.values())
                    flash(f"Error: Total split amounts (${total_splits:.2f}) don't match expense amount (${amount:.2f})", 'error')
                    return render_template('add_expense.html')
                
                # Set the unequal split amounts
                for participant in participants:
                    participant.amount_owed = unequal_splits.get(participant.name, 0.0)
            
            expense.calculate_splits()
            
            # Validate that amounts balance correctly
            if expense.split_type == SplitType.UNEQUAL:
                total_owed = sum(p.amount_owed for p in expense.participants)
                if abs(total_owed - expense.amount) > 0.01:
                    flash(f"Error: Split amounts (${total_owed:.2f}) don't match expense total (${expense.amount:.2f})", 'error')
                    return render_template('add_expense.html')
            
            if not expense.validate_payments():
                total_paid = sum(p.amount_paid for p in expense.participants) + sum(expense.external_payments.values())
                flash(f"Error: Total payments (${total_paid:.2f}) don't match expense amount (${expense.amount:.2f})", 'error')
                return render_template('add_expense.html')
            
            expenses.append(expense)
            flash('Expense added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError as e:
            flash(f"Error: Invalid input - {str(e)}", 'error')
            return render_template('add_expense.html')
        except Exception as e:
            flash(f"Error: {str(e)}", 'error')
            return render_template('add_expense.html')
    
    return render_template('add_expense.html')

@app.route('/expense/<expense_id>')
def view_expense(expense_id):
    expense = next((e for e in expenses if e.id == expense_id), None)
    if not expense:
        return "Expense not found", 404
    
    balance_summary = expense.get_balance_summary()
    return render_template('expense_detail.html', expense=expense, balances=balance_summary)

@app.route('/edit_expense/<expense_id>', methods=['GET', 'POST'])
def edit_expense(expense_id):
    expense = next((e for e in expenses if e.id == expense_id), None)
    if not expense:
        flash('Expense not found', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Store previous payers before updating
            previous_payer_names = [name.strip() for name in expense.paid_by.split(',') if name.strip()]
            
            expense.title = request.form['title']
            expense.amount = float(request.form['amount'])
            expense.paid_by = request.form['paid_by']
            # Parse multiple payers from the tag system  
            payer_names = [name.strip() for name in expense.paid_by.split(',') if name.strip()]
            participants_str = request.form['participants']
            expense.split_type = SplitType(request.form['split_type'])
            expense.payment_type = PaymentType(request.form['payment_type'])
            expense.category = request.form.get('category', '') or None
            
            # Parse participants from the participants field (same as add expense)
            participant_names = [name.strip() for name in participants_str.split(',') if name.strip()]
            
            # Validate that at least one participant is selected
            if not participant_names:
                flash("Error: At least one participant must be selected. Someone needs to owe money for this expense.", 'error')
                return render_template('edit_expense.html', expense=expense)
            
            expense.participants = [Participant(name=name) for name in participant_names]
            
            # Important: Recalculate splits immediately after changing participants
            # This ensures equal splits are redistributed among the new participant list
            if expense.split_type == SplitType.EQUAL:
                expense.calculate_splits()
            elif expense.split_type == SplitType.UNEQUAL:
                # For unequal splits, we need to preserve existing amounts for remaining participants
                # but reset amounts for new participants to 0 (they'll be set from form data later)
                pass  # Unequal amounts will be handled later from form data
            
            # Handle payments based on payment type
            payments = {}
            # Reset all participant payments to 0 first
            for participant in expense.participants:
                payments[participant.name] = 0.0
            
            # Also reset all previous payers to 0 (including those who might not be participants)
            for previous_payer in previous_payer_names:
                payments[previous_payer] = 0.0
            
            if expense.payment_type == PaymentType.EQUAL:
                # Distribute payment equally among current payers
                per_payer_amount = expense.amount / len(payer_names) if payer_names else expense.amount
                for payer_name in payer_names:
                    payments[payer_name] = per_payer_amount
            else:  # PaymentType.UNEQUAL
                # Get unequal payment amounts from form
                unequal_payments = {}
                for payer_name in payer_names:
                    payment_field = f'payment_amount_{payer_name}'
                    if payment_field in request.form:
                        unequal_payments[payer_name] = float(request.form[payment_field])
                    else:
                        unequal_payments[payer_name] = 0.0
                
                # Validate unequal payments total
                if not expense.validate_unequal_payments(unequal_payments):
                    total_payments = sum(unequal_payments.values())
                    flash(f"Error: Total payments (${total_payments:.2f}) don't match expense amount (${expense.amount:.2f})", 'error')
                    return render_template('edit_expense.html', expense=expense)
                
                # Set the unequal payment amounts
                for payer_name, payment_amount in unequal_payments.items():
                    payments[payer_name] = payment_amount
            
                
            expense.set_payments(payments)
            
            # Handle split amounts based on split type
            if expense.split_type == SplitType.UNEQUAL:
                # Get unequal split amounts from form
                unequal_splits = {}
                for participant in expense.participants:
                    split_field = f'split_amount_{participant.name}'
                    if split_field in request.form:
                        unequal_splits[participant.name] = float(request.form[split_field])
                    else:
                        unequal_splits[participant.name] = 0.0
                
                # Validate unequal splits total
                if not expense.validate_unequal_splits(unequal_splits):
                    total_splits = sum(unequal_splits.values())
                    flash(f"Error: Total split amounts (${total_splits:.2f}) don't match expense amount (${expense.amount:.2f})", 'error')
                    return render_template('edit_expense.html', expense=expense)
                
                # Set the unequal split amounts
                for participant in expense.participants:
                    participant.amount_owed = unequal_splits.get(participant.name, 0.0)
            
            expense.calculate_splits()
            
            # Validate that amounts balance correctly
            if expense.split_type == SplitType.UNEQUAL:
                total_owed = sum(p.amount_owed for p in expense.participants)
                if abs(total_owed - expense.amount) > 0.01:
                    flash(f"Error: Split amounts (${total_owed:.2f}) don't match expense total (${expense.amount:.2f})", 'error')
                    return render_template('edit_expense.html', expense=expense)
            
            if not expense.validate_payments():
                total_paid = sum(p.amount_paid for p in expense.participants) + sum(expense.external_payments.values())
                flash(f"Error: Total payments (${total_paid:.2f}) don't match expense amount (${expense.amount:.2f})", 'error')
                return render_template('edit_expense.html', expense=expense)
            
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('view_expense', expense_id=expense_id))
            
        except ValueError as e:
            flash(f"Error: Invalid input - {str(e)}", 'error')
            return render_template('edit_expense.html', expense=expense)
        except Exception as e:
            flash(f"Error: {str(e)}", 'error')
            return render_template('edit_expense.html', expense=expense)
    
    return render_template('edit_expense.html', expense=expense)

@app.route('/delete_expense/<expense_id>', methods=['POST'])
def delete_expense(expense_id):
    global expenses
    expenses = [e for e in expenses if e.id != expense_id]
    return redirect(url_for('index'))

@app.route('/api/participants')
def get_participants():
    all_participants = set()
    for expense in expenses:
        all_participants.add(expense.paid_by)
        for participant in expense.participants:
            all_participants.add(participant.name)
    return jsonify(list(all_participants))

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)