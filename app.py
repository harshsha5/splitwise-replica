from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from datetime import datetime
import uuid
from models import Expense, Participant, SplitType

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

@app.route('/')
def index():
    user_balance = get_user_net_balance(CURRENT_USER)
    return render_template('index.html', expenses=expenses, user_balance=user_balance, current_user=CURRENT_USER)

@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        try:
            title = request.form['title']
            amount = float(request.form['amount'])
            paid_by = request.form['paid_by']
            participants_str = request.form['participants']
            split_type = SplitType(request.form['split_type'])
            category = request.form.get('category', '')
            
            # Auto-include payer in participants if not already there
            participant_names = [name.strip() for name in participants_str.split(',') if name.strip()]
            if paid_by not in participant_names:
                participant_names.append(paid_by)
            
            # Validate that at least one participant exists
            if not participant_names:
                flash("Error: At least one participant must be specified. Someone needs to owe money for this expense.", 'error')
                return render_template('add_expense.html')
            
            participants = [Participant(name=name) for name in participant_names]
            
            expense = Expense(
                id=str(uuid.uuid4()),
                title=title,
                amount=amount,
                paid_by=paid_by,
                participants=participants,
                split_type=split_type,
                date=datetime.now(),
                category=category if category else None
            )
            
            # Handle payments - iterate through all form fields to find payment amounts
            payments = {}
            for key, value in request.form.items():
                if key.startswith('payment_amount_'):
                    try:
                        index = int(key.split('_')[2])
                        if index < len(participants):
                            participant_name = participants[index].name
                            payments[participant_name] = float(value) if value else 0.0
                    except (ValueError, IndexError):
                        continue
            
            # Ensure all participants have a payment amount (default to 0)
            for participant in participants:
                if participant.name not in payments:
                    payments[participant.name] = 0.0
            
            # If no custom payments specified, default to primary payer paying full amount
            if sum(payments.values()) == 0:
                payments[paid_by] = amount
                
            expense.set_payments(payments)
            
            # Handle custom split amounts - iterate through all form fields
            if split_type == SplitType.CUSTOM:
                for key, value in request.form.items():
                    if key.startswith('custom_amount_'):
                        try:
                            index = int(key.split('_')[2])
                            if index < len(participants) and value:
                                participants[index].amount_owed = float(value)
                        except (ValueError, IndexError):
                            continue
            
            expense.calculate_splits()
            
            # Validate that amounts balance correctly
            if expense.split_type == SplitType.CUSTOM:
                total_owed = sum(p.amount_owed for p in expense.participants)
                if abs(total_owed - expense.amount) > 0.01:
                    flash(f"Error: Custom split amounts (${total_owed:.2f}) don't match expense total (${expense.amount:.2f})", 'error')
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
            expense.title = request.form['title']
            expense.amount = float(request.form['amount'])
            expense.paid_by = request.form['paid_by']
            participants_str = request.form['participants']
            expense.split_type = SplitType(request.form['split_type'])
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
            elif expense.split_type == SplitType.CUSTOM:
                # For custom splits, we need to preserve existing amounts for remaining participants
                # but reset amounts for new participants to 0 (they'll be set from form data later)
                pass  # Custom amounts will be handled later from form data
            
            # Handle payments - iterate through all form fields to find payment amounts
            payments = {}
            for key, value in request.form.items():
                if key.startswith('payment_amount_'):
                    try:
                        index = int(key.split('_')[2])
                        if index < len(expense.participants):
                            participant_name = expense.participants[index].name
                            payments[participant_name] = float(value) if value else 0.0
                    except (ValueError, IndexError):
                        continue
            
            # Ensure all participants have a payment amount (default to 0)
            for participant in expense.participants:
                if participant.name not in payments:
                    payments[participant.name] = 0.0
            
            # If no custom payments specified, default to primary payer paying full amount
            if sum(payments.values()) == 0:
                payments[expense.paid_by] = expense.amount
            
                
            expense.set_payments(payments)
            
            # Handle custom split amounts - iterate through all form fields
            if expense.split_type == SplitType.CUSTOM:
                for key, value in request.form.items():
                    if key.startswith('custom_amount_'):
                        try:
                            index = int(key.split('_')[2])
                            if index < len(expense.participants) and value:
                                expense.participants[index].amount_owed = float(value)
                        except (ValueError, IndexError):
                            continue
            
            expense.calculate_splits()
            
            # Validate that amounts balance correctly
            if expense.split_type == SplitType.CUSTOM:
                total_owed = sum(p.amount_owed for p in expense.participants)
                if abs(total_owed - expense.amount) > 0.01:
                    flash(f"Error: Custom split amounts (${total_owed:.2f}) don't match expense total (${expense.amount:.2f})", 'error')
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
    app.run(debug=True, host='127.0.0.1', port=5000)