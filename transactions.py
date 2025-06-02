import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import platform
from datetime import datetime
from db_operations import get_parking_history, get_last_unpaid_entry, update_payment_status

class TransactionWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Parking Management System - Transactions")
        self.root.geometry("800x600")
        
        # Configure grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Search Frame
        search_frame = ttk.Frame(root, padding="10")
        search_frame.grid(row=0, column=0, sticky="ew")
        
        ttk.Label(search_frame, text="Plate Number:").pack(side=tk.LEFT, padx=5)
        self.plate_entry = ttk.Entry(search_frame)
        self.plate_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="Search", command=self.search_transactions).pack(side=tk.LEFT, padx=5)
        
        # Transactions Frame
        transactions_frame = ttk.Frame(root, padding="10")
        transactions_frame.grid(row=1, column=0, sticky="nsew")
        
        # Treeview
        self.tree = ttk.Treeview(transactions_frame, columns=("Plate", "Status", "Entry Time", "Payment Time", "Amount"), show="headings")
        self.tree.heading("Plate", text="Plate Number")
        self.tree.heading("Status", text="Payment Status")
        self.tree.heading("Entry Time", text="Entry Time")
        self.tree.heading("Payment Time", text="Payment Time")
        self.tree.heading("Amount", text="Amount Paid")
        
        # Column widths
        self.tree.column("Plate", width=100)
        self.tree.column("Status", width=100)
        self.tree.column("Entry Time", width=150)
        self.tree.column("Payment Time", width=150)
        self.tree.column("Amount", width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(transactions_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def search_transactions(self):
        plate = self.plate_entry.get().strip().upper()
        if not plate:
            messagebox.showwarning("Warning", "Please enter a plate number")
            return
            
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Get transactions from database
        transactions = get_parking_history(plate)
        
        if not transactions:
            messagebox.showinfo("Info", f"No transactions found for plate {plate}")
            return
            
        # Add transactions to tree
        for transaction in transactions:
            status = "Paid" if transaction['payment_status'] else "Unpaid"
            payment_time = transaction['payment_timestamp'].strftime('%Y-%m-%d %H:%M:%S') if transaction['payment_timestamp'] else "-"
            amount = f"₱{transaction['amount_paid']:.2f}" if transaction['amount_paid'] else "-"
            
            self.tree.insert("", tk.END, values=(
                transaction['plate_number'],
                status,
                transaction['entry_timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                payment_time,
                amount
            ))

def main():
    root = tk.Tk()
    app = TransactionWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()